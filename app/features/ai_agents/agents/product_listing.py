from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent, ModelRetry, RunContext

from app.config import settings
from app.core.ai_agents.deps import AgentDeps, bind_dynamic_system_prompt, tool_db_session
from app.core.ai_agents.registry import AgentDefinition, register_agent
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.features.categories import service as categories_service
from app.features.media.schemas import MediaItem
from app.features.products import service as products_service
from app.features.products.schemas import ProductCreate, ProductStatusFilter

SYSTEM_PROMPT = """\
You help a Pulse Store admin draft new product listings through conversation.

Ask for whatever is missing from: name, SKU, brand, category, retail price, cost price,
stock quantity, status (ACTIVE/DRAFT/INACTIVE/OUT_OF_STOCK), and optionally description,
tags and images. Use list_categories to resolve a category name to its id, and
check_sku_available before proposing a SKU.

Once you have everything, summarize the draft in plain language and ask the admin to
confirm. Only call create_product_draft after the admin has explicitly confirmed —
never create a product on the first message.

Images: the admin uploads pictures separately through the existing media upload feature
and pastes/attaches the resulting image info into the chat — you never handle raw image
files yourself.
"""

agent = Agent(deps_type=AgentDeps)
bind_dynamic_system_prompt(agent)


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str


class ProductDraftResult(BaseModel):
    success: bool
    product_id: Optional[int] = None
    slug: Optional[str] = None


@agent.tool
def list_categories(ctx: RunContext[AgentDeps], search: Optional[str] = None) -> list[CategoryOut]:
    """List existing product categories, optionally filtered by name, to resolve a category to its id.

    Some providers mishandle a tool with no parameters at all (sending null instead of {}
    as the call arguments), so this always keeps at least one real, useful parameter.
    """
    with tool_db_session() as db:
        result = categories_service.get_categories(db, search=search, limit=200)
        return [CategoryOut(id=c.id, name=c.name, slug=c.slug) for c in result["data"]]


@agent.tool
def check_sku_available(ctx: RunContext[AgentDeps], sku: str) -> bool:
    """Check whether a SKU is still available before proposing it for a new product."""
    with tool_db_session() as db:
        return not products_service.sku_exists(db, sku)


@agent.tool
def create_product_draft(
    ctx: RunContext[AgentDeps],
    name: str,
    sku: str,
    brand: str,
    retail_price: str,
    cost_price: str,
    stock_quantity: int,
    category_id: int,
    status: ProductStatusFilter,
    tags: Optional[list[str]] = None,
    description: Optional[str] = None,
    media: Optional[list[MediaItem]] = None,
) -> ProductDraftResult:
    """Create the product. Only call this after the admin has confirmed the drafted details.

    retail_price/cost_price are plain decimal strings (e.g. "29.99") rather than a numeric
    type: some tool-calling providers (Groq) reject the JSON schema pydantic generates for
    Decimal parameters, so the conversion happens here instead of in the tool signature.
    """
    if ctx.deps.is_first_message:
        raise ModelRetry(
            "Do not create the product yet. Summarize the drafted details for the admin "
            "and ask them to confirm first; only call this tool after their next message."
        )

    try:
        product_in = ProductCreate(
            name=name,
            sku=sku,
            brand=brand,
            description=description,
            retail_price=Decimal(retail_price),
            cost_price=Decimal(cost_price),
            stock_quantity=stock_quantity,
            category_id=category_id,
            status=status,
            tags=tags or [],
            media=media or [],
        )
    except (ValidationError, InvalidOperation) as exc:
        raise ModelRetry(str(exc)) from exc

    try:
        with tool_db_session() as db:
            product = products_service.create_product(db, product_in)
    except (ConflictException, NotFoundException, BadRequestException) as exc:
        raise ModelRetry(str(exc.detail)) from exc

    return ProductDraftResult(success=True, product_id=product.id, slug=product.slug)


register_agent(
    AgentDefinition(
        key="product_listing",
        display_name="Product Listing Assistant",
        agent=agent,
        default_model=settings.AI_DEFAULT_MODEL,
        default_system_prompt=SYSTEM_PROMPT,
        requires_admin=True,
    )
)
