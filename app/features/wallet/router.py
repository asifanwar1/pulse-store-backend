from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_user
from app.features.users.models import User
from app.features.wallet import service
from app.features.wallet.schemas import (
    AttachPaymentMethodRequest,
    PayOrderRequest,
    PayOrderResponse,
    SetupIntentResponse,
    WalletConfigResponse,
    WalletPaymentMethodListResponse,
    WalletPaymentMethodResponse,
)

router = APIRouter()


@router.get("/config", response_model=WalletConfigResponse)
def get_wallet_config():
    return service.get_wallet_config()


@router.post("/setup-intent", response_model=SetupIntentResponse)
def create_setup_intent(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client_secret = service.create_setup_intent(db, current_user)
    return SetupIntentResponse(client_secret=client_secret)


@router.post("/payment-methods", response_model=WalletPaymentMethodResponse, status_code=201)
def attach_payment_method(
    payload: AttachPaymentMethodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.attach_payment_method(db, current_user, payload.payment_method_id)


@router.get("/payment-methods", response_model=WalletPaymentMethodListResponse)
def list_payment_methods(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.list_payment_methods(db, current_user)


@router.patch("/payment-methods/{payment_method_id}/default", response_model=WalletPaymentMethodResponse)
def set_default_payment_method(
    payment_method_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.set_default_payment_method(db, current_user, payment_method_id)


@router.delete("/payment-methods/{payment_method_id}", status_code=204)
def delete_payment_method(
    payment_method_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.delete_payment_method(db, current_user, payment_method_id)


@router.post("/pay", response_model=PayOrderResponse)
def pay_for_order(
    payload: PayOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.pay_for_order(db, current_user, payload.order_id, payload.payment_method_id)
