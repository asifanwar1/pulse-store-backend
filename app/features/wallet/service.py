from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.money import to_decimal
from app.features.notifications import service as notifications_service
from app.features.notifications.models import NotificationType
from app.features.orders import service as orders_service
from app.features.orders.models import Order, OrderPaymentStatus, OrderStatus
from app.features.users.models import User
from app.features.wallet.models import PaymentStatus, Wallet, WalletPaymentMethod, WalletTransaction
from app.features.wallet.schemas import PayOrderResponse, PayOrderStatus, WalletConfigResponse

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_wallet_config() -> WalletConfigResponse:
    return WalletConfigResponse(publishable_key=settings.STRIPE_PUBLISHABLE_KEY)


def _get_wallet_or_none(db: Session, user: User) -> Optional[Wallet]:
    return db.query(Wallet).filter(Wallet.user_id == user.id).first()


def get_or_create_wallet(db: Session, user: User) -> Wallet:
    wallet = _get_wallet_or_none(db, user)
    if wallet:
        return wallet

    try:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user.id)},
        )
    except stripe.error.StripeError as error:
        raise BadRequestException(str(error))

    wallet = Wallet(user_id=user.id, stripe_customer_id=customer.id)
    db.add(wallet)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _get_wallet_or_none(db, user)
        if existing:
            return existing
        raise
    db.refresh(wallet)
    return wallet


def create_setup_intent(db: Session, user: User) -> str:
    wallet = get_or_create_wallet(db, user)
    try:
        intent = stripe.SetupIntent.create(
            customer=wallet.stripe_customer_id, payment_method_types=["card"])
    except stripe.error.StripeError as error:
        raise BadRequestException(str(error))
    return intent.client_secret


def attach_payment_method(db: Session, user: User, stripe_payment_method_id: str) -> WalletPaymentMethod:
    wallet = get_or_create_wallet(db, user)

    db.query(Wallet).filter(Wallet.id == wallet.id).with_for_update().first()

    if db.query(WalletPaymentMethod).filter(WalletPaymentMethod.stripe_payment_method_id == stripe_payment_method_id).first():
        raise ConflictException("Payment method already saved")

    try:
        attached = stripe.PaymentMethod.attach(
            stripe_payment_method_id, customer=wallet.stripe_customer_id)
    except stripe.error.StripeError as error:
        raise BadRequestException(str(error))

    if attached.card is None:
        raise BadRequestException("Only card payment methods are supported")

    is_first = db.query(WalletPaymentMethod).filter(
        WalletPaymentMethod.wallet_id == wallet.id).count() == 0

    wallet_payment_method = WalletPaymentMethod(
        wallet_id=wallet.id,
        stripe_payment_method_id=stripe_payment_method_id,
        brand=attached.card.brand,
        last4=attached.card.last4,
        exp_month=attached.card.exp_month,
        exp_year=attached.card.exp_year,
        is_default=is_first,
    )
    db.add(wallet_payment_method)
    db.commit()
    db.refresh(wallet_payment_method)
    return wallet_payment_method


def list_payment_methods(db: Session, user: User) -> dict:
    wallet = _get_wallet_or_none(db, user)
    if not wallet:
        return {"data": [], "count": 0}
    methods = (
        db.query(WalletPaymentMethod)
        .filter(WalletPaymentMethod.wallet_id == wallet.id)
        .order_by(WalletPaymentMethod.created_at.desc())
        .all()
    )
    return {"data": methods, "count": len(methods)}


def _get_owned_payment_method(db: Session, wallet: Wallet, payment_method_id: int) -> WalletPaymentMethod:
    payment_method = (
        db.query(WalletPaymentMethod)
        .filter(WalletPaymentMethod.id == payment_method_id, WalletPaymentMethod.wallet_id == wallet.id)
        .first()
    )
    if not payment_method:
        raise NotFoundException("Payment method not found")
    return payment_method


def set_default_payment_method(db: Session, user: User, payment_method_id: int) -> WalletPaymentMethod:
    wallet = _get_wallet_or_none(db, user)
    if not wallet:
        raise NotFoundException("Payment method not found")
    payment_method = _get_owned_payment_method(db, wallet, payment_method_id)

    db.query(WalletPaymentMethod).filter(
        WalletPaymentMethod.wallet_id == wallet.id, WalletPaymentMethod.id != payment_method.id
    ).update({"is_default": False})
    payment_method.is_default = True
    db.commit()
    db.refresh(payment_method)
    return payment_method


def delete_payment_method(db: Session, user: User, payment_method_id: int) -> None:
    wallet = _get_wallet_or_none(db, user)
    if not wallet:
        raise NotFoundException("Payment method not found")
    payment_method = _get_owned_payment_method(db, wallet, payment_method_id)

    was_default = payment_method.is_default
    try:
        stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
    except stripe.error.StripeError:
        pass

    db.delete(payment_method)
    db.flush()

    if was_default:
        remaining = (
            db.query(WalletPaymentMethod)
            .filter(WalletPaymentMethod.wallet_id == wallet.id)
            .order_by(WalletPaymentMethod.created_at.desc())
            .first()
        )
        if remaining:
            remaining.is_default = True

    db.commit()


def _resolve_payment_method(db: Session, wallet: Wallet, payment_method_id: Optional[int]) -> WalletPaymentMethod:
    if payment_method_id is not None:
        return _get_owned_payment_method(db, wallet, payment_method_id)

    payment_method = (
        db.query(WalletPaymentMethod)
        .filter(WalletPaymentMethod.wallet_id == wallet.id, WalletPaymentMethod.is_default.is_(True))
        .first()
    )
    if not payment_method:
        raise BadRequestException(
            "No saved payment method. Connect a card first.")
    return payment_method


def _record_transaction(
    db: Session,
    wallet: Wallet,
    order: Order,
    status: PaymentStatus,
    *,
    stripe_payment_intent_id: Optional[str] = None,
    failure_message: Optional[str] = None,
) -> WalletTransaction:
    transaction = WalletTransaction(
        wallet_id=wallet.id,
        order_id=order.id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        amount=order.total_amount,
        currency=settings.DEFAULT_CURRENCY,
        status=status,
        failure_message=failure_message,
    )
    db.add(transaction)
    return transaction


def pay_for_order(db: Session, user: User, order_id: int, payment_method_id: Optional[int]) -> PayOrderResponse:

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.user_id == user.id)
        .with_for_update()
        .first()
    )
    if not order:
        raise NotFoundException("Order not found")
    if order.payment_status == OrderPaymentStatus.PAID:
        raise ConflictException("Order is already paid")

    wallet = _get_wallet_or_none(db, user)
    if not wallet:
        raise BadRequestException(
            "No saved payment method. Connect a card first.")
    payment_method = _resolve_payment_method(db, wallet, payment_method_id)

    amount_cents = int((to_decimal(order.total_amount) *
                       100).to_integral_value(rounding=ROUND_HALF_UP))
    idempotency_key = f"order-{order.id}-{payment_method.stripe_payment_method_id}"

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=settings.DEFAULT_CURRENCY,
            customer=wallet.stripe_customer_id,
            payment_method=payment_method.stripe_payment_method_id,
            payment_method_types=["card"],
            confirm=True,
            idempotency_key=idempotency_key,
        )
    except stripe.error.CardError as error:
        details = error.error
        failure_message = (details.message if details else None) or str(error)
        failed_intent_id = details.payment_intent.id if details and details.payment_intent else None
        _record_transaction(db, wallet, order, PaymentStatus.FAILED,
                            stripe_payment_intent_id=failed_intent_id, failure_message=failure_message)
        db.commit()
        notifications_service.create_notification(
            db,
            user.id,
            NotificationType.WALLET_PAYMENT_FAILED,
            title="Payment failed",
            body=f"Payment for order #{order.id} failed: {failure_message}",
            entity_type="order",
            entity_id=order.id,
        )
        return PayOrderResponse(status=PayOrderStatus.FAILED, order_id=order.id, message=failure_message)
    except stripe.error.StripeError as error:

        _record_transaction(db, wallet, order,
                            PaymentStatus.FAILED, failure_message=str(error))
        db.commit()
        notifications_service.create_notification(
            db,
            user.id,
            NotificationType.WALLET_PAYMENT_FAILED,
            title="Payment failed",
            body=f"Payment for order #{order.id} could not be processed.",
            entity_type="order",
            entity_id=order.id,
        )
        raise BadRequestException(f"Payment could not be processed: {error}")

    if intent.status == "succeeded":
        _record_transaction(
            db, wallet, order, PaymentStatus.SUCCEEDED, stripe_payment_intent_id=intent.id)
        order.payment_status = OrderPaymentStatus.PAID
        if order.status == OrderStatus.PENDING:
            orders_service.apply_order_status(order, OrderStatus.PROCESSING, note="Payment received")
        db.commit()
        notifications_service.create_notification(
            db,
            user.id,
            NotificationType.WALLET_PAYMENT_SUCCEEDED,
            title="Payment successful",
            body=f"Your payment for order #{order.id} was successful.",
            entity_type="order",
            entity_id=order.id,
        )
        return PayOrderResponse(status=PayOrderStatus.SUCCEEDED, order_id=order.id)

    if intent.status == "requires_action":
        _record_transaction(
            db, wallet, order, PaymentStatus.REQUIRES_ACTION, stripe_payment_intent_id=intent.id)
        db.commit()
        return PayOrderResponse(
            status=PayOrderStatus.REQUIRES_ACTION,
            order_id=order.id,
            client_secret=intent.client_secret,
        )

    if intent.status == "processing":
        _record_transaction(
            db, wallet, order, PaymentStatus.PROCESSING, stripe_payment_intent_id=intent.id)
        db.commit()
        return PayOrderResponse(
            status=PayOrderStatus.PROCESSING,
            order_id=order.id,
            message="Payment is still processing. We'll update your order once it clears.",
        )

    _record_transaction(
        db, wallet, order, PaymentStatus.FAILED,
        stripe_payment_intent_id=intent.id,
        failure_message=f"Unexpected payment status: {intent.status}",
    )
    db.commit()
    return PayOrderResponse(
        status=PayOrderStatus.FAILED,
        order_id=order.id,
        message=f"Payment could not be completed (status: {intent.status})",
    )


def handle_stripe_webhook(db: Session, payload: bytes, sig_header: Optional[str]) -> None:
    """Reconcile orders against async Stripe payment outcomes (3-D Secure, delayed
    processing) that pay_for_order's synchronous response can't observe."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise BadRequestException("Stripe webhook is not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise BadRequestException("Invalid webhook signature")

    event_type = event["type"]
    if event_type not in ("payment_intent.succeeded", "payment_intent.payment_failed", "payment_intent.processing"):
        return

    intent = event["data"]["object"]

    transaction = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.stripe_payment_intent_id == intent["id"])
        .first()
    )
    if not transaction:
        return

    order = (
        db.query(Order)
        .filter(Order.id == transaction.order_id)
        .with_for_update()
        .first()
    )
    if not order or order.payment_status == OrderPaymentStatus.PAID:
        return

    if event_type == "payment_intent.succeeded":
        if transaction.status == PaymentStatus.SUCCEEDED:
            return
        transaction.status = PaymentStatus.SUCCEEDED
        order.payment_status = OrderPaymentStatus.PAID
        if order.status == OrderStatus.PENDING:
            orders_service.apply_order_status(order, OrderStatus.PROCESSING, note="Payment received")
        db.commit()
        notifications_service.create_notification(
            db,
            order.user_id,
            NotificationType.WALLET_PAYMENT_SUCCEEDED,
            title="Payment successful",
            body=f"Your payment for order #{order.id} was successful.",
            entity_type="order",
            entity_id=order.id,
        )
    elif event_type == "payment_intent.payment_failed":
        if transaction.status == PaymentStatus.FAILED:
            return
        last_error = intent["last_payment_error"] if "last_payment_error" in intent else None
        transaction.status = PaymentStatus.FAILED
        transaction.failure_message = last_error["message"] if last_error and "message" in last_error else None
        db.commit()
        notifications_service.create_notification(
            db,
            order.user_id,
            NotificationType.WALLET_PAYMENT_FAILED,
            title="Payment failed",
            body=f"Payment for order #{order.id} failed: {transaction.failure_message or 'unknown error'}",
            entity_type="order",
            entity_id=order.id,
        )
    elif event_type == "payment_intent.processing":
        if transaction.status == PaymentStatus.PROCESSING:
            return
        transaction.status = PaymentStatus.PROCESSING
        db.commit()
