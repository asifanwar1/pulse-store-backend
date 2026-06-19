from sqlalchemy.orm import Session, joinedload
from app.features.cart.models import Cart, CartItem
from app.features.cart.schemas import CartItemAdd, CartItemUpdate
from app.features.products.models import Product
from app.core.exceptions import NotFoundException


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        # ensure relationships are loaded
        cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.id == cart.id).first()
    return cart


def add_item(db: Session, user_id: int, item_in: CartItemAdd) -> Cart:
    cart = get_or_create_cart(db, user_id)
    product = db.query(Product).filter(Product.id == item_in.product_id).first()
    if not product:
        raise NotFoundException("Product not found")
    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item_in.product_id,
    ).first()
    if existing:
        existing.quantity += item_in.quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=item_in.product_id, quantity=item_in.quantity))
    db.commit()
    # reload cart with items and product relations
    cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.id == cart.id).first()
    return cart


def update_item(db: Session, user_id: int, item_id: int, item_in: CartItemUpdate) -> Cart:
    cart = get_or_create_cart(db, user_id)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise NotFoundException("Cart item not found")
    item.quantity = item_in.quantity
    db.commit()
    cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.id == cart.id).first()
    return cart


def remove_item(db: Session, user_id: int, item_id: int) -> Cart:
    cart = get_or_create_cart(db, user_id)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise NotFoundException("Cart item not found")
    db.delete(item)
    db.commit()
    cart = db.query(Cart).options(joinedload(Cart.items).joinedload(CartItem.product)).filter(Cart.id == cart.id).first()
    return cart


def clear_cart(db: Session, user_id: int) -> None:
    cart = get_or_create_cart(db, user_id)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
