import pytest
from pydantic_ai import ModelRetry
from sqlalchemy import text

from app.core.ai_agents.deps import AgentDeps
from app.database import SessionLocal
from app.features.ai_agents.agents.product_listing import create_product_draft, update_product_draft
from app.features.ai_agents.models import Conversation
from app.features.categories.models import Category
from app.features.products.models import Product
from app.features.products.schemas import ProductStatusFilter
from app.features.users.models import User, UserStatus, UserType


class _FakeRunContext:
    """create_product_draft/update_product_draft only read ctx.deps, so this is enough
    to stand in for pydantic_ai's real RunContext."""

    def __init__(self, deps):
        self.deps = deps


@pytest.fixture
def real_db():
    """A genuinely committed, cross-connection-visible session.

    The rollback-based `db_session` fixture (see conftest.py) never truly commits at the
    database level, so it's invisible to the tools under test, which each open their own
    independent session via tool_db_session() -- by design, so concurrent tool calls in the
    same turn don't share a sync SQLAlchemy Session (see AgentDeps's docstring).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_user(db):
    user = User(
        email="product-listing-tool-test@example.com",
        full_name="Tool Test User",
        address={},
        user_type=UserType.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        hashed_password="x",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_category(db):
    category = Category(name="Tool Test Category", slug="tool-test-category")
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _make_conversation(db, user_id):
    conversation = Conversation(agent_key="product_listing", user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _cleanup(db, *, conversation_id=None, product_id=None, category_id=None, user_id=None):
    """Raw SQL, deliberately bypassing the ORM: by this point `db` has already loaded and
    expired several of these rows over the course of the test, and Query.delete() can miss
    a row whose identity-map state is stale in ways a plain DELETE statement never sees."""
    if conversation_id is not None:
        db.execute(text("DELETE FROM ai_conversations WHERE id = :id"), {"id": conversation_id})
    if product_id is not None:
        db.execute(text("DELETE FROM products WHERE id = :id"), {"id": product_id})
    if category_id is not None:
        db.execute(text("DELETE FROM categories WHERE id = :id"), {"id": category_id})
    if user_id is not None:
        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    db.commit()


def test_update_product_draft_refuses_when_nothing_created_yet(real_db):
    user = _make_user(real_db)
    conversation = _make_conversation(real_db, user.id)
    try:
        deps = AgentDeps(
            current_user=user, system_prompt="", conversation_id=conversation.id, is_first_message=False
        )
        ctx = _FakeRunContext(deps)

        with pytest.raises(ModelRetry):
            update_product_draft(ctx, name="Should not apply")
    finally:
        _cleanup(real_db, conversation_id=conversation.id, user_id=user.id)


def test_update_product_draft_only_changes_the_product_this_conversation_created(real_db):
    user = _make_user(real_db)
    category = _make_category(real_db)
    conversation = _make_conversation(real_db, user.id)
    product_id = None
    try:
        deps = AgentDeps(
            current_user=user, system_prompt="", conversation_id=conversation.id, is_first_message=False
        )
        ctx = _FakeRunContext(deps)

        created = create_product_draft(
            ctx,
            name="Original Name",
            sku="TOOL-TEST-SKU-1",
            brand="Test Brand",
            retail_price="10.00",
            cost_price="5.00",
            stock_quantity=5,
            category_id=category.id,
            status=ProductStatusFilter.ACTIVE,
        )
        assert created.success
        product_id = created.product_id

        updated = update_product_draft(ctx, name="Natural Beauty Care Pack")
        assert updated.success
        assert updated.product_id == product_id

        real_db.expire_all()
        product = real_db.query(Product).filter(Product.id == product_id).first()
        assert product.name == "Natural Beauty Care Pack"

        conversation_row = real_db.query(Conversation).filter(Conversation.id == conversation.id).first()
        assert conversation_row.created_product_id == product_id
    finally:
        _cleanup(
            real_db,
            conversation_id=conversation.id,
            product_id=product_id,
            category_id=category.id,
            user_id=user.id,
        )
