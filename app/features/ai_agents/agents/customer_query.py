from typing import Optional

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext

from app.config import settings
from app.core.ai_agents.deps import AgentDeps, bind_dynamic_system_prompt, tool_db_session
from app.core.ai_agents.registry import AgentDefinition, register_agent
from app.core.exceptions import NotFoundException
from app.features.ai_agents import service as ai_service
from app.features.orders import service as orders_service
from app.features.products import service as products_service
from app.features.products.schemas import ProductStatusFilter

SYSTEM_PROMPT = """\
You answer customer questions about orders and products for Pulse Store.

FAQ:
- Shipping takes 3-5 business days for standard delivery.
- Returns are accepted within 30 days of delivery, in original condition.
- Refunds are issued to the original payment method within 5-7 business days of an
  approved return.

Use find_product and get_order_status to answer from real data instead of guessing. If you
cannot resolve the customer's issue with the tools and FAQ above, or they ask for a human,
call escalate_to_human with a short subject and summary — don't just apologize and stop.

An admin can edit this FAQ text and your other instructions from the admin dashboard.
"""

agent = Agent(deps_type=AgentDeps)
bind_dynamic_system_prompt(agent)


class ProductSummary(BaseModel):
    product_id: int
    name: str
    price: str
    slug: str


class OrderLookupResult(BaseModel):
    found: bool
    order_id: Optional[int] = None
    status: Optional[str] = None
    payment_status: Optional[str] = None
    message: Optional[str] = None


class EscalationResult(BaseModel):
    ticket_id: int


@agent.tool
def find_product(ctx: RunContext[AgentDeps], query: str) -> list[ProductSummary]:
    """Search active products by name, brand or category to answer a product question."""
    with tool_db_session() as db:
        result = products_service.get_products(db, search=query, limit=5, status=ProductStatusFilter.ACTIVE)
        return [ProductSummary(product_id=p.id, name=p.name, price=f"{p.price:.2f}", slug=p.slug) for p in result["data"]]


@agent.tool
def get_order_status(ctx: RunContext[AgentDeps], order_id: int) -> OrderLookupResult:
    """Look up an order's status and payment status by its id, scoped to the current customer."""
    with tool_db_session() as db:
        try:
            order = orders_service.get_order_by_id(db, order_id)
        except NotFoundException as exc:
            raise ModelRetry(str(exc.detail)) from exc

        if not ctx.deps.current_user.is_admin and order.user_id != ctx.deps.current_user.id:
            return OrderLookupResult(found=False, message="No order with that id was found for your account.")

        return OrderLookupResult(
            found=True,
            order_id=order.id,
            status=order.status.value if order.status else None,
            payment_status=order.payment_status.value if order.payment_status else None,
        )


@agent.tool
def escalate_to_human(ctx: RunContext[AgentDeps], subject: str, summary: str) -> EscalationResult:
    """Hand off to a human admin when the question can't be resolved from tools/FAQ, or on request."""
    if ctx.deps.conversation_id is None:
        raise ModelRetry("No active conversation to escalate.")
    with tool_db_session() as db:
        ticket = ai_service.create_support_ticket(
            db,
            conversation_id=ctx.deps.conversation_id,
            user_id=ctx.deps.current_user.id,
            subject=subject,
            message=summary,
        )
        return EscalationResult(ticket_id=ticket.id)


register_agent(
    AgentDefinition(
        key="customer_query",
        display_name="Customer Query Assistant",
        agent=agent,
        default_model=settings.AI_DEFAULT_MODEL,
        default_system_prompt=SYSTEM_PROMPT,
        requires_admin=False,
    )
)
