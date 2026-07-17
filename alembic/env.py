from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.config import settings
from app.database import Base

# Import all models so their tables are registered with Base.metadata
from app.features.users.models import User  # noqa: F401
from app.features.categories.models import Category  # noqa: F401
from app.features.products.models import Product  # noqa: F401
from app.features.orders.models import Order, OrderItem, OrderStatusHistory  # noqa: F401
from app.features.shipments.models import Shipment, ShipmentTrackingEvent  # noqa: F401
from app.features.cart.models import Cart, CartItem  # noqa: F401
from app.features.auth.models import OTPCode  # noqa: F401
from app.features.banners.models import Banner  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
