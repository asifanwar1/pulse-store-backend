import os

from dotenv import load_dotenv

load_dotenv()


def _derive_test_db_url(url: str) -> str:
    base, _, dbname = url.rpartition("/")
    if not dbname.endswith("-test"):
        dbname += "-test"
    return f"{base}/{dbname}"


os.environ["DATABASE_URL"] = _derive_test_db_url(os.environ["DATABASE_URL"])
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
os.environ["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_placeholder"
# Force-disable real SMTP sends -- send_otp_email() raises (and is swallowed by the
# caller) instead of attempting a network connection when these are unset.
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.limiter import limiter
from decimal import Decimal

from app.core.security import create_access_token, hash_password
from app.database import Base, SessionLocal, engine
from app.dependencies import get_db
from app.features.categories.models import Category
from app.features.products.models import Product
from app.features.users.models import User, UserStatus, UserType
from app.main import app


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield

DEFAULT_PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture(scope="session", autouse=True)
def _prepare_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db_session():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = SessionLocal(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    def _make(
        email: str,
        password: str = DEFAULT_PASSWORD,
        user_type: str = UserType.CUSTOMER.value,
        full_name: str = "Test User",
        verified: bool = True,
        active: bool = True,
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            address={},
            user_type=user_type,
            status=UserStatus.ACTIVE.value if active else UserStatus.INACTIVE.value,
            hashed_password=hash_password(password),
            is_active=active,
            is_verified=verified,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def make_category(db_session):
    def _make(name: str = "Test Category") -> Category:
        category = Category(name=name, slug=name.lower().replace(" ", "-"))
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        return category

    return _make


@pytest.fixture()
def make_product(db_session, make_category):
    def _make(
        sku: str,
        name: str = "Test Product",
        price: str = "10.00",
        cost_price: str = "5.00",
        stock_quantity: int = 10,
        category: Category | None = None,
        is_active: bool = True,
    ) -> Product:
        product = Product(
            name=name,
            sku=sku,
            brand="Test Brand",
            slug=f"{name.lower().replace(' ', '-')}-{sku.lower()}",
            price=Decimal(price),
            cost_price=Decimal(cost_price),
            stock_quantity=stock_quantity,
            category_id=(category or make_category()).id,
            is_active=is_active,
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product

    return _make


@pytest.fixture()
def auth_headers():
    def _headers(user: User) -> dict:
        token = create_access_token({"sub": str(user.id), "tv": user.token_version})
        return {"Authorization": f"Bearer {token}"}

    return _headers
