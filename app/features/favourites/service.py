from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.features.favourites.models import Favourite
from app.features.favourites.schemas import FavouriteListResponse, FavouriteToggleResponse
from app.features.offers import service as offers_service
from app.features.products.models import Product


def toggle_favourite(db: Session, user_id: int, product_id: int) -> FavouriteToggleResponse:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundException("Product not found")

    favourite = (
        db.query(Favourite)
        .filter(Favourite.user_id == user_id, Favourite.product_id == product_id)
        .first()
    )
    if favourite:
        db.delete(favourite)
        db.commit()
        return FavouriteToggleResponse(product_id=product_id, is_favourited=False)

    db.add(Favourite(user_id=user_id, product_id=product_id))
    db.commit()
    return FavouriteToggleResponse(product_id=product_id, is_favourited=True)


def get_favourite_products(db: Session, user_id: int) -> FavouriteListResponse:
    products = (
        db.query(Product)
        .join(Favourite, Favourite.product_id == Product.id)
        .filter(Favourite.user_id == user_id)
        .order_by(Favourite.created_at.desc())
        .all()
    )
    offers_service.annotate_products_with_offers(db, products)
    return FavouriteListResponse(data=products, count=len(products))


def remove_product_favourite_links(db: Session, product_id: int) -> None:
    db.query(Favourite).filter(Favourite.product_id == product_id).delete(synchronize_session=False)
