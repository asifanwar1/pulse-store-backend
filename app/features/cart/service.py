from sqlalchemy.orm import Session, joinedload
from app.features.cart.models import Cart, CartItem
from app.features.cart.schemas import CartItemAdd, CartItemUpdate
from app.features.offers import service as offers_service
from app.features.products.models import Product
from app.core.exceptions import ConflictException, NotFoundException


def _load_cart(db: Session, user_id: int) -> Cart:
    cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        # ensure relationships are loaded
        cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.id == cart.id).first()
    return cart


def _annotate_cart(cart: Cart, db: Session) -> Cart:
    offers_service.annotate_products_with_offers(db, [item.product for item in cart.items])
    return cart


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    return _annotate_cart(_load_cart(db, user_id), db)


def _ensure_purchasable(product: Product, requested_quantity: int) -> None:
    """Validate a product can be added/updated in a cart at the given quantity.

    Mirrors the checks orders/service.py's create_order performs before
    creating order items, so cart and checkout reject the same way.
    """
    if not product.is_active:
        raise ConflictException(f"Product is not available: {product.name}")
    if product.stock_quantity < requested_quantity:
        raise ConflictException(f"Insufficient stock for product: {product.name}")


def add_item(db: Session, user_id: int, item_in: CartItemAdd) -> Cart:
    cart = _load_cart(db, user_id)
    product = db.query(Product).filter(Product.id == item_in.product_id).first()
    if not product:
        raise NotFoundException("Product not found")
    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item_in.product_id,
    ).first()
    requested_quantity = (existing.quantity if existing else 0) + item_in.quantity
    _ensure_purchasable(product, requested_quantity)
    if existing:
        existing.quantity = requested_quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=item_in.product_id, quantity=item_in.quantity))
    db.commit()
    # reload cart with items and product relations
    cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.id == cart.id).first()
    return _annotate_cart(cart, db)


def update_item(db: Session, user_id: int, item_id: int, item_in: CartItemUpdate) -> Cart:
    cart = _load_cart(db, user_id)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise NotFoundException("Cart item not found")
    _ensure_purchasable(item.product, item_in.quantity)
    item.quantity = item_in.quantity
    db.commit()
    cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.id == cart.id).first()
    return _annotate_cart(cart, db)


def remove_item(db: Session, user_id: int, item_id: int) -> Cart:
    cart = _load_cart(db, user_id)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise NotFoundException("Cart item not found")
    db.delete(item)
    db.commit()
    cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.id == cart.id).first()
    return _annotate_cart(cart, db)


def clear_cart(db: Session, user_id: int) -> None:
    cart = _load_cart(db, user_id)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
