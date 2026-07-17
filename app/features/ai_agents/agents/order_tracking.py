from typing import Optional

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext

from app.config import settings
from app.core.ai_agents.deps import AgentDeps, bind_dynamic_system_prompt, tool_db_session
from app.core.ai_agents.registry import AgentDefinition, register_agent
from app.core.exceptions import NotFoundException
from app.features.orders import service as orders_service
from app.features.shipments import service as shipments_service

SYSTEM_PROMPT = """\
You help admins and customers check the status of orders and shipments for Pulse Store.

Customers can only see their own orders — if a lookup comes back "not found for your
account", tell them exactly that rather than guessing why. Admins can look up any order.
Use get_order_status for an order id, track_shipment for a shipment tracking number, and
list_my_recent_orders when someone doesn't have an id/tracking number handy.
"""

agent = Agent(deps_type=AgentDeps)
bind_dynamic_system_prompt(agent)

_MAX_RECENT_ORDERS = 10


class OrderLookupResult(BaseModel):
    found: bool
    order_id: Optional[int] = None
    status: Optional[str] = None
    payment_status: Optional[str] = None
    total_amount: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    message: Optional[str] = None


class ShipmentLookupResult(BaseModel):
    found: bool
    tracking_id: Optional[str] = None
    status: Optional[str] = None
    courier: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    delivered_at: Optional[str] = None
    message: Optional[str] = None


class OrderSummary(BaseModel):
    order_id: int
    status: str
    total_amount: str


def _owns_order(ctx: RunContext[AgentDeps], order_user_id: int) -> bool:
    return ctx.deps.current_user.is_admin or order_user_id == ctx.deps.current_user.id


@agent.tool
def get_order_status(ctx: RunContext[AgentDeps], order_id: int) -> OrderLookupResult:
    """Look up an order's current status, payment status and delivery estimate by its id."""
    with tool_db_session() as db:
        try:
            order = orders_service.get_order_by_id(db, order_id)
        except NotFoundException as exc:
            raise ModelRetry(str(exc.detail)) from exc

        if not _owns_order(ctx, order.user_id):
            return OrderLookupResult(found=False, message="No order with that id was found for your account.")

        return OrderLookupResult(
            found=True,
            order_id=order.id,
            status=order.status.value if order.status else None,
            payment_status=order.payment_status.value if order.payment_status else None,
            total_amount=f"{order.total_amount:.2f}",
            estimated_delivery_date=str(order.estimated_delivery_date) if order.estimated_delivery_date else None,
        )


@agent.tool
def track_shipment(ctx: RunContext[AgentDeps], tracking_id: str) -> ShipmentLookupResult:
    """Look up a shipment's status and delivery estimate by its tracking number."""
    with tool_db_session() as db:
        try:
            shipment = shipments_service.get_shipment_by_tracking_id(db, tracking_id)
        except NotFoundException as exc:
            raise ModelRetry(str(exc.detail)) from exc

        if not _owns_order(ctx, shipment.order.user_id):
            return ShipmentLookupResult(
                found=False, message="No shipment with that tracking id was found for your account."
            )

        return ShipmentLookupResult(
            found=True,
            tracking_id=shipment.tracking_id,
            status=shipment.status.value if shipment.status else None,
            courier=shipment.courier,
            estimated_delivery_date=str(shipment.estimated_delivery_date) if shipment.estimated_delivery_date else None,
            delivered_at=str(shipment.delivered_at) if shipment.delivered_at else None,
        )


@agent.tool
def list_my_recent_orders(ctx: RunContext[AgentDeps], limit: int = 5) -> list[OrderSummary]:
    """List recent orders when the user doesn't have an order id or tracking number handy."""
    capped_limit = min(limit, _MAX_RECENT_ORDERS)
    with tool_db_session() as db:
        result = orders_service.get_orders(
            db,
            user_id=None if ctx.deps.current_user.is_admin else ctx.deps.current_user.id,
            limit=capped_limit,
        )
        return [
            OrderSummary(order_id=o.id, status=o.status.value if o.status else "", total_amount=f"{o.total_amount:.2f}")
            for o in result["data"]
        ]


register_agent(
    AgentDefinition(
        key="order_tracking",
        display_name="Order Tracking Assistant",
        agent=agent,
        default_model=settings.AI_DEFAULT_MODEL,
        default_system_prompt=SYSTEM_PROMPT,
        requires_admin=False,
    )
)
