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


def _create_order(client, auth_headers, user, product, quantity=1):
    create_resp = client.post(
        "/api/v1/orders/",
        json={
            "user_id": user.id,
            "items": [{"product_id": product.id, "quantity": quantity}],
            "payment_method": "COD",
        },
        headers=auth_headers(user),
    )
    assert create_resp.status_code == 201
    return create_resp.json()["id"]


def test_order_status_endpoint_rejects_direct_shipping_transition(client, make_product, make_user, auth_headers):
    """Regression test: an order can no longer become SHIPPING (or SHIPPED/DELIVERED)
    without a Shipment row backing it -- that used to leave it invisible in the
    shipment listing forever. Moving into shipping now requires create_shipment."""
    product = make_product(sku="NO-DIRECT-SHIP-1", stock_quantity=5)
    user = make_user("no-direct-ship-buyer@example.com")
    admin = make_user("no-direct-ship-admin@example.com", user_type=UserType.ADMIN.value)
    order_id = _create_order(client, auth_headers, user, product)

    for status in ("SHIPPING", "SHIPPED", "DELIVERED"):
        resp = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": status},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 400, status


def test_creating_shipment_makes_order_visible_in_shipment_listing(client, make_product, make_user, auth_headers):
    """The originally reported bug: an order in a shipping state must show up in the
    shipment listing and detail view. Since SHIPPING is now only reachable by creating
    a shipment, this holds for every order that reaches it."""
    product = make_product(sku="VISIBLE-SHIP-1", stock_quantity=5)
    user = make_user("visible-ship-buyer@example.com")
    admin = make_user("visible-ship-admin@example.com", user_type=UserType.ADMIN.value)
    order_id = _create_order(client, auth_headers, user, product)

    shipment_resp = client.post(
        "/api/v1/shipments/",
        json={
            "order_id": order_id,
            "tracking_id": "TRACK-VISIBLE-1",
            "shipment_method": "STANDARD",
            "courier": "Test Courier",
            "status": "PENDING",
        },
        headers=auth_headers(admin),
    )
    assert shipment_resp.status_code == 201
    shipment_id = shipment_resp.json()["id"]

    order_resp = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(admin))
    assert order_resp.json()["status"] == "SHIPPING"

    listing_resp = client.get(
        "/api/v1/shipments/", params={"order_id": order_id}, headers=auth_headers(admin)
    )
    assert listing_resp.status_code == 200
    listed_ids = [row["id"] for row in listing_resp.json()["data"]]
    assert shipment_id in listed_ids

    detail_resp = client.get(f"/api/v1/shipments/{shipment_id}", headers=auth_headers(admin))
    assert detail_resp.status_code == 200
    assert detail_resp.json()["order_id"] == order_id


def test_order_status_endpoint_blocked_once_shipment_exists(client, make_product, make_user, auth_headers):
    """Once a shipment exists, all further progress must go through the shipment
    endpoints so order/shipment status can never drift apart again."""
    product = make_product(sku="LOCKED-SHIP-1", stock_quantity=5)
    user = make_user("locked-ship-buyer@example.com")
    admin = make_user("locked-ship-admin@example.com", user_type=UserType.ADMIN.value)
    order_id = _create_order(client, auth_headers, user, product)

    shipment_resp = client.post(
        "/api/v1/shipments/",
        json={
            "order_id": order_id,
            "tracking_id": "TRACK-LOCKED-1",
            "shipment_method": "STANDARD",
            "courier": "Test Courier",
            "status": "PENDING",
        },
        headers=auth_headers(admin),
    )
    assert shipment_resp.status_code == 201

    resp = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 409


def test_shipment_progression_to_delivered_updates_order(client, make_product, make_user, auth_headers):
    """From the shipment, status can be advanced all the way to DELIVERED, and the
    parent order follows it."""
    product = make_product(sku="PROGRESS-SHIP-1", stock_quantity=5)
    user = make_user("progress-ship-buyer@example.com")
    admin = make_user("progress-ship-admin@example.com", user_type=UserType.ADMIN.value)
    order_id = _create_order(client, auth_headers, user, product)

    shipment_resp = client.post(
        "/api/v1/shipments/",
        json={
            "order_id": order_id,
            "tracking_id": "TRACK-PROGRESS-1",
            "shipment_method": "STANDARD",
            "courier": "Test Courier",
            "status": "PENDING",
        },
        headers=auth_headers(admin),
    )
    shipment_id = shipment_resp.json()["id"]

    for status in ("SHIPPED", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"):
        resp = client.patch(
            f"/api/v1/shipments/{shipment_id}/status",
            json={"status": status},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200, status

    order_resp = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(admin))
    assert order_resp.json()["status"] == "DELIVERED"


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
