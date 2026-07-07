from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class WalletConfigResponse(BaseModel):
    publishable_key: str


class SetupIntentResponse(BaseModel):
    client_secret: str


class AttachPaymentMethodRequest(BaseModel):
    payment_method_id: str


class WalletPaymentMethodResponse(BaseModel):
    id: int
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WalletPaymentMethodListResponse(BaseModel):
    data: list[WalletPaymentMethodResponse]
    count: int


class PayOrderRequest(BaseModel):
    order_id: int
    payment_method_id: Optional[int] = None


class PayOrderStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    REQUIRES_ACTION = "REQUIRES_ACTION"
    FAILED = "FAILED"


class PayOrderResponse(BaseModel):
    status: PayOrderStatus
    order_id: int
    client_secret: Optional[str] = None
    message: Optional[str] = None
