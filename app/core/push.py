import json
import logging
from typing import Optional

import firebase_admin
import httpx
from firebase_admin import credentials, messaging

from app.config import settings

logger = logging.getLogger(__name__)

_app: Optional[firebase_admin.App] = None
_init_attempted = False

EXPO_PUSH_API_URL = "https://exp.host/--/api/v2/push/send"


def _get_app() -> Optional[firebase_admin.App]:
    """Lazily initialize the Firebase Admin SDK from settings.

    Returns None (and logs once) if FIREBASE_CREDENTIALS_JSON isn't configured,
    so callers can no-op instead of crashing the request -- notifications are
    still written to the DB even when push isn't set up yet.
    """
    global _app, _init_attempted
    if _app is not None or _init_attempted:
        return _app
    _init_attempted = True

    if not settings.FIREBASE_CREDENTIALS_JSON:
        logger.warning("FIREBASE_CREDENTIALS_JSON is not configured; push notifications are disabled.")
        return None

    try:
        raw = settings.FIREBASE_CREDENTIALS_JSON
        cred_info = json.loads(raw) if raw.strip().startswith("{") else raw
        cred = credentials.Certificate(cred_info)
        _app = firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID} if settings.FIREBASE_PROJECT_ID else None)
    except Exception:
        logger.exception("Failed to initialize the Firebase Admin SDK; push notifications are disabled.")
        _app = None
    return _app


def send_fcm_push(tokens: list[str], title: str, body: str, data: Optional[dict] = None) -> list[str]:
    """Send a push notification to Firebase Cloud Messaging tokens (browsers
    registered via the Firebase Web SDK).

    Returns the subset of tokens Firebase reported as invalid/unregistered, so
    callers can clean them up. No-ops (returns []) if Firebase isn't configured
    or there are no tokens to send to.
    """
    if not tokens:
        return []

    app = _get_app()
    if app is None:
        return []

    string_data = {key: str(value) for key, value in (data or {}).items()}
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=string_data,
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message, app=app)
    except Exception:
        logger.exception("Failed to send FCM push notification to %d token(s)", len(tokens))
        return []

    invalid_tokens = []
    for token, result in zip(tokens, response.responses):
        if result.success:
            continue
        error_code = getattr(result.exception, "code", None)
        if error_code in ("NOT_FOUND", "UNREGISTERED", "INVALID_ARGUMENT"):
            invalid_tokens.append(token)
        else:
            logger.warning("FCM push failed for a token: %s", result.exception)
    return invalid_tokens


def send_expo_push(tokens: list[str], title: str, body: str, data: Optional[dict] = None) -> list[str]:
    """Send a push notification to Expo push tokens (the Expo-managed mobile
    app), via Expo's push HTTP API. Expo relays these to FCM/APNs using the
    credentials configured in the app's EAS project, so this backend never
    handles raw Android/iOS platform tokens.

    Returns the subset of tokens Expo reported as no-longer-registered, so
    callers can clean them up. No-ops (returns []) if there are no tokens.
    """
    if not tokens:
        return []

    string_data = {key: str(value) for key, value in (data or {}).items()}
    messages = [{"to": token, "title": title, "body": body, "data": string_data} for token in tokens]

    try:
        response = httpx.post(EXPO_PUSH_API_URL, json=messages, timeout=10)
        response.raise_for_status()
        results = response.json().get("data", [])
    except httpx.HTTPError:
        logger.exception("Failed to send Expo push notification to %d token(s)", len(tokens))
        return []

    invalid_tokens = []
    for token, result in zip(tokens, results):
        if result.get("status") != "error":
            continue
        if result.get("details", {}).get("error") == "DeviceNotRegistered":
            invalid_tokens.append(token)
        else:
            logger.warning("Expo push failed for a token: %s", result.get("message"))
    return invalid_tokens
