import hashlib
import hmac
import json
import threading
import time
from decimal import Decimal

import stripe

from app.database import SessionLocal
from app.features.orders.models import Order, OrderPaymentStatus, OrderStatus, PaymentMethod
from app.features.wallet import service as wallet_service
from app.features.wallet.models import PaymentStatus, Wallet, WalletTransaction

WEBHOOK_SECRET = "whsec_test_secret"


def _sign(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload.decode()}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def _stripe_event(event_type: str, intent_id: str, **intent_extra) -> bytes:
    body = {
        "id": "evt_test_1",
        "object": "event",
        "type": event_type,
        "data": {"object": {"id": intent_id, "object": "payment_intent", **intent_extra}},
    }
    return json.dumps(body).encode()


def _make_order_with_transaction(db, *, payment_status=OrderPaymentStatus.UNPAID, transaction_status=PaymentStatus.PROCESSING):
    from app.core.security import hash_password
    from app.features.users.models import User, UserStatus, UserType

    user = User(
        email=f"wallet-{transaction_status.value.lower()}-{id(db)}@example.com",
        full_name="Wallet Tester",
        address={},
        user_type=UserType.CUSTOMER.value,
        status=UserStatus.ACTIVE.value,
        hashed_password=hash_password("Str0ng!Pass1"),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    wallet = Wallet(user_id=user.id, stripe_customer_id=f"cus_{user.id}")
    db.add(wallet)
    db.flush()

    order = Order(
        user_id=user.id,
        status=OrderStatus.PENDING,
        payment_method=PaymentMethod.card,
        payment_status=payment_status,
        total_amount=Decimal("25.00"),
    )
    db.add(order)
    db.flush()

    transaction = WalletTransaction(
        wallet_id=wallet.id,
        order_id=order.id,
        stripe_payment_intent_id=f"pi_{order.id}",
        amount=order.total_amount,
        currency="usd",
        status=transaction_status,
    )
    db.add(transaction)
    db.commit()
    return order, transaction


def test_webhook_rejects_invalid_signature(client):
    payload = _stripe_event("payment_intent.succeeded", "pi_does_not_matter")
    response = client.post(
        "/api/v1/wallet/webhook",
        content=payload,
        headers={"Stripe-Signature": "t=123,v1=deadbeef"},
    )
    assert response.status_code == 400


def test_webhook_marks_order_paid_on_succeeded(db_session):
    order, transaction = _make_order_with_transaction(db_session)
    payload = _stripe_event("payment_intent.succeeded", transaction.stripe_payment_intent_id)
    signature = _sign(payload)

    wallet_service.handle_stripe_webhook(db_session, payload, signature)

    db_session.refresh(order)
    db_session.refresh(transaction)
    assert order.payment_status == OrderPaymentStatus.PAID
    assert order.status == OrderStatus.PROCESSING
    assert transaction.status == PaymentStatus.SUCCEEDED


def test_webhook_marks_transaction_failed(db_session):
    order, transaction = _make_order_with_transaction(db_session)
    payload = _stripe_event(
        "payment_intent.payment_failed",
        transaction.stripe_payment_intent_id,
        last_payment_error={"message": "Your card was declined."},
    )
    signature = _sign(payload)

    wallet_service.handle_stripe_webhook(db_session, payload, signature)

    db_session.refresh(order)
    db_session.refresh(transaction)
    assert order.payment_status == OrderPaymentStatus.UNPAID
    assert transaction.status == PaymentStatus.FAILED
    assert transaction.failure_message == "Your card was declined."


def test_webhook_is_idempotent_for_already_paid_orders(db_session):
    order, transaction = _make_order_with_transaction(
        db_session, payment_status=OrderPaymentStatus.PAID, transaction_status=PaymentStatus.SUCCEEDED
    )
    payload = _stripe_event("payment_intent.succeeded", transaction.stripe_payment_intent_id)
    signature = _sign(payload)

    # Must not raise or double-process an already-reconciled order.
    wallet_service.handle_stripe_webhook(db_session, payload, signature)

    db_session.refresh(order)
    assert order.payment_status == OrderPaymentStatus.PAID


def test_concurrent_wallet_creation_does_not_duplicate(monkeypatch):
    from app.core.security import hash_password
    from app.features.users.models import User, UserStatus, UserType

    class _FakeCustomer:
        id = "cus_fake_race"

    monkeypatch.setattr(stripe.Customer, "create", lambda **kwargs: _FakeCustomer())

    db = SessionLocal()
    try:
        user = User(
            email="wallet-race@example.com",
            full_name="Wallet Racer",
            address={},
            user_type=UserType.CUSTOMER.value,
            status=UserStatus.ACTIVE.value,
            hashed_password=hash_password("Str0ng!Pass1"),
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    def _create_wallet():
        thread_db = SessionLocal()
        try:
            thread_user = thread_db.query(User).filter(User.id == user_id).first()
            wallet_service.get_or_create_wallet(thread_db, thread_user)
        finally:
            thread_db.close()

    threads = [threading.Thread(target=_create_wallet) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    verify_db = SessionLocal()
    try:
        wallets = verify_db.query(Wallet).filter(Wallet.user_id == user_id).all()
        assert len(wallets) == 1
    finally:
        verify_db.close()
