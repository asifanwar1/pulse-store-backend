import threading
from decimal import Decimal

from app.core.exceptions import ConflictException
from app.core.security import hash_password
from app.database import SessionLocal
from app.features.categories.models import Category
from app.features.orders import service as orders_service
from app.features.orders.models import OrderStatus, PaymentMethod
from app.features.orders.schemas import OrderCreate, OrderItemCreate
from app.features.products.models import Product
from app.features.users.models import User, UserStatus, UserType


def test_total_sales_endpoint_requires_admin(client, make_product, make_user, auth_headers):
    product = make_product(sku="TS-1")

    unauthenticated = client.patch(f"/api/v1/products/{product.id}/total-sales", json={"total_sales": 5})
    assert unauthenticated.status_code == 401

    non_admin = make_user("nonadmin-ts@example.com")
    forbidden = client.patch(
        f"/api/v1/products/{product.id}/total-sales",
        json={"total_sales": 5},
        headers=auth_headers(non_admin),
    )
    assert forbidden.status_code == 403

    admin = make_user("admin-ts@example.com", user_type=UserType.ADMIN.value)
    ok = client.patch(
        f"/api/v1/products/{product.id}/total-sales",
        json={"total_sales": 5},
        headers=auth_headers(admin),
    )
    assert ok.status_code == 200
    assert ok.json()["total_sales"] == 5


def test_cart_rejects_non_positive_quantity(client, make_product, make_user, auth_headers):
    product = make_product(sku="CART-NEG-1")
    user = make_user("cartneg@example.com")
    headers = auth_headers(user)

    response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 0},
        headers=headers,
    )
    assert response.status_code == 422

    response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": -3},
        headers=headers,
    )
    assert response.status_code == 422


def test_order_rejects_non_positive_quantity(client, make_product, make_user, auth_headers):
    product = make_product(sku="ORDER-NEG-1")
    user = make_user("orderneg@example.com")

    response = client.post(
        "/api/v1/orders/",
        json={
            "user_id": user.id,
            "items": [{"product_id": product.id, "quantity": -1}],
            "payment_method": "COD",
        },
        headers=auth_headers(user),
    )
    assert response.status_code == 422


def test_order_cancellation_restocks_inventory(client, make_product, make_user, auth_headers):
    product = make_product(sku="RESTOCK-1", stock_quantity=5)
    user = make_user("restock-buyer@example.com")
    admin = make_user("restock-admin@example.com", user_type=UserType.ADMIN.value)

    create_resp = client.post(
        "/api/v1/orders/",
        json={
            "user_id": user.id,
            "items": [{"product_id": product.id, "quantity": 3}],
            "payment_method": "COD",
        },
        headers=auth_headers(user),
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    product_after_order = client.get(f"/api/v1/products/{product.id}").json()
    assert product_after_order["stock_quantity"] == 2

    cancel_resp = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=auth_headers(admin),
    )
    assert cancel_resp.status_code == 200

    product_after_cancel = client.get(f"/api/v1/products/{product.id}").json()
    assert product_after_cancel["stock_quantity"] == 5


def test_order_status_cannot_change_once_cancelled(client, make_product, make_user, auth_headers):
    product = make_product(sku="TERMINAL-1", stock_quantity=5)
    user = make_user("terminal-buyer@example.com")
    admin = make_user("terminal-admin@example.com", user_type=UserType.ADMIN.value)

    create_resp = client.post(
        "/api/v1/orders/",
        json={
            "user_id": user.id,
            "items": [{"product_id": product.id, "quantity": 1}],
            "payment_method": "COD",
        },
        headers=auth_headers(user),
    )
    order_id = create_resp.json()["id"]

    cancel_resp = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=auth_headers(admin),
    )
    assert cancel_resp.status_code == 200

    reopen_resp = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "PROCESSING"},
        headers=auth_headers(admin),
    )
    assert reopen_resp.status_code == 409


def test_shipment_update_cannot_change_status_of_terminal_order(client, make_product, make_user, auth_headers):
    """Regression test: the terminal-state guard must apply uniformly whether an
    order's status changes via the direct admin endpoint or via shipment syncing."""
    product = make_product(sku="SHIP-TERMINAL-1", stock_quantity=5)
    user = make_user("ship-terminal-buyer@example.com")
    admin = make_user("ship-terminal-admin@example.com", user_type=UserType.ADMIN.value)

    create_resp = client.post(
        "/api/v1/orders/",
        json={
            "user_id": user.id,
            "items": [{"product_id": product.id, "quantity": 1}],
            "payment_method": "COD",
        },
        headers=auth_headers(user),
    )
    order_id = create_resp.json()["id"]

    cancel_resp = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=auth_headers(admin),
    )
    assert cancel_resp.status_code == 200

    shipment_resp = client.post(
        "/api/v1/shipments/",
        json={
            "order_id": order_id,
            "tracking_id": "TRACK-TERMINAL-1",
            "shipment_method": "STANDARD",
            "courier": "Test Courier",
            "status": "DELIVERED",
        },
        headers=auth_headers(admin),
    )
    assert shipment_resp.status_code == 409


def test_concurrent_orders_cannot_oversell_stock():
    """Regression test for the stock race condition: two simultaneous orders
    for the last unit of stock must not both succeed."""
    db = SessionLocal()
    try:
        category = Category(name="Race Category", slug="race-category")
        db.add(category)
        db.flush()
        product = Product(
            name="Race Product",
            sku="RACE-SKU-1",
            brand="Race Brand",
            slug="race-product-1",
            price=Decimal("10.00"),
            cost_price=Decimal("5.00"),
            stock_quantity=1,
            category_id=category.id,
        )
        db.add(product)
        user = User(
            email="racer@example.com",
            full_name="Racer",
            address={},
            user_type=UserType.CUSTOMER.value,
            status=UserStatus.ACTIVE.value,
            hashed_password=hash_password("Str0ng!Pass1"),
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        product_id = product.id
        user_id = user.id
    finally:
        db.close()

    results = []

    def _attempt_order():
        thread_db = SessionLocal()
        try:
            order_in = OrderCreate(
                user_id=user_id,
                items=[OrderItemCreate(product_id=product_id, quantity=1)],
                payment_method=PaymentMethod.cod,
            )
            orders_service.create_order(thread_db, order_in, actor_user_id=user_id)
            results.append("success")
        except ConflictException:
            results.append("conflict")
        finally:
            thread_db.close()

    threads = [threading.Thread(target=_attempt_order) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == ["conflict", "success"]

    verify_db = SessionLocal()
    try:
        final_product = verify_db.query(Product).filter(Product.id == product_id).first()
        assert final_product.stock_quantity == 0
        assert verify_db.query(Product).filter(Product.id == product_id).count() == 1
    finally:
        verify_db.close()
