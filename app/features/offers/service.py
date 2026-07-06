from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Sequence

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.money import to_decimal
from app.features.categories.models import Category
from app.features.offers.models import Offer, OfferProduct, OfferScope
from app.features.offers.schemas import OfferCreate, OfferStatus, OfferUpdate
from app.features.products.models import Product


SORTABLE_OFFER_COLUMNS = {
    "id": Offer.id,
    "name": Offer.name,
    "discount_percentage": Offer.discount_percentage,
    "start_date": Offer.start_date,
    "end_date": Offer.end_date,
    "created_at": Offer.created_at,
    "updated_at": Offer.updated_at,
}


@dataclass
class OfferMatch:
    offer_id: int
    offer_name: str
    discount_percentage: Decimal
    discounted_price: Decimal


def _get_live_offers(db: Session, now: datetime) -> list[Offer]:
    return (
        db.query(Offer)
        .options(selectinload(Offer.categories), selectinload(Offer.product_links))
        .filter(Offer.is_active.is_(True), Offer.start_date <= now, Offer.end_date >= now)
        .order_by(Offer.id.asc())
        .all()
    )


def compute_offer_matches(db: Session, products: Sequence[Product]) -> dict[int, OfferMatch]:
    if not products:
        return {}

    now = datetime.now(timezone.utc)
    live_offers = _get_live_offers(db, now)
    if not live_offers:
        return {}

    category_parents = dict(db.query(Category.id, Category.parent_id).all())
    ancestor_cache: dict[int, set[int]] = {}

    def ancestor_ids(category_id: int) -> set[int]:
        if category_id in ancestor_cache:
            return ancestor_cache[category_id]
        ids: set[int] = set()
        current: Optional[int] = category_id
        while current is not None and current not in ids:
            ids.add(current)
            current = category_parents.get(current)
        ancestor_cache[category_id] = ids
        return ids

    prepared_offers = [
        (
            offer,
            {link.product_id: link.is_excluded for link in offer.product_links},
            {category.id for category in offer.categories},
        )
        for offer in live_offers
    ]

    matches: dict[int, OfferMatch] = {}
    for product in products:
        best: Optional[Offer] = None
        for offer, exclusion_map, offer_category_ids in prepared_offers:
            if product.id in exclusion_map:
                if exclusion_map[product.id]:
                    continue
                qualifies = True
            elif offer.scope == OfferScope.ALL_CATEGORIES:
                qualifies = True
            elif product.category_id is None:
                qualifies = False
            else:
                qualifies = bool(ancestor_ids(product.category_id) & offer_category_ids)

            if qualifies and (best is None or offer.discount_percentage > best.discount_percentage):
                best = offer

        if best is not None:
            discounted_price = (
                to_decimal(product.price) * (Decimal("1") - best.discount_percentage / Decimal("100"))
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            matches[product.id] = OfferMatch(
                offer_id=best.id,
                offer_name=best.name,
                discount_percentage=best.discount_percentage,
                discounted_price=discounted_price,
            )

    return matches


def annotate_products_with_offers(db: Session, products: Sequence[Product]) -> None:
    matches = compute_offer_matches(db, products)
    for product in products:
        match = matches.get(product.id)
        product.discount_percentage = match.discount_percentage if match else None
        product.discounted_price = match.discounted_price if match else None
        product.offer_name = match.offer_name if match else None


def get_effective_price(db: Session, product: Product) -> Decimal:
    match = compute_offer_matches(db, [product]).get(product.id)
    return match.discounted_price if match else to_decimal(product.price)


def remove_product_offer_links(db: Session, product_id: int) -> None:
    db.query(OfferProduct).filter(OfferProduct.product_id == product_id).delete(synchronize_session=False)


def _attach_product_summaries(offer: Offer) -> None:
    offer.included_products = [link.product for link in offer.product_links if not link.is_excluded]
    offer.excluded_products = [link.product for link in offer.product_links if link.is_excluded]


def _require_categories(db: Session, category_ids: list[int]) -> list[Category]:
    if not category_ids:
        return []
    categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
    missing = set(category_ids) - {category.id for category in categories}
    if missing:
        raise NotFoundException(f"Categories not found: {sorted(missing)}")
    return categories


def _require_products(db: Session, product_ids: list[int]) -> list[Product]:
    if not product_ids:
        return []
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    missing = set(product_ids) - {product.id for product in products}
    if missing:
        raise NotFoundException(f"Products not found: {sorted(missing)}")
    return products


def get_offers(
    db: Session,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    scope: Optional[OfferScope] = None,
    is_active: Optional[bool] = None,
    status: Optional[OfferStatus] = None,
) -> dict:
    query = db.query(Offer).options(selectinload(Offer.categories), selectinload(Offer.product_links).selectinload(OfferProduct.product))

    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(or_(Offer.name.ilike(search_term), Offer.description.ilike(search_term)))

    if scope is not None:
        query = query.filter(Offer.scope == scope)

    if is_active is not None:
        query = query.filter(Offer.is_active.is_(is_active))

    if status is not None:
        now = datetime.now(timezone.utc)
        if status == OfferStatus.DISABLED:
            query = query.filter(Offer.is_active.is_(False))
        elif status == OfferStatus.UPCOMING:
            query = query.filter(Offer.is_active.is_(True), Offer.start_date > now)
        elif status == OfferStatus.ACTIVE:
            query = query.filter(Offer.is_active.is_(True), Offer.start_date <= now, Offer.end_date >= now)
        elif status == OfferStatus.EXPIRED:
            query = query.filter(Offer.is_active.is_(True), Offer.end_date < now)

    total_count = query.count()
    offset = (page - 1) * limit
    offers = query.order_by(Offer.created_at.desc()).offset(offset).limit(limit).all()
    for offer in offers:
        _attach_product_summaries(offer)
    return {"data": offers, "count": total_count}


def get_offer_by_id(db: Session, offer_id: int) -> Offer:
    offer = (
        db.query(Offer)
        .options(selectinload(Offer.categories), selectinload(Offer.product_links).selectinload(OfferProduct.product))
        .filter(Offer.id == offer_id)
        .first()
    )
    if not offer:
        raise NotFoundException("Offer not found")
    _attach_product_summaries(offer)
    return offer


def create_offer(db: Session, offer_in: OfferCreate) -> Offer:
    categories = _require_categories(db, offer_in.category_ids)
    included_products = _require_products(db, offer_in.included_product_ids)
    excluded_products = _require_products(db, offer_in.excluded_product_ids)

    offer = Offer(
        name=offer_in.name,
        description=offer_in.description,
        discount_percentage=offer_in.discount_percentage,
        scope=offer_in.scope,
        start_date=offer_in.start_date,
        end_date=offer_in.end_date,
        is_active=offer_in.is_active,
        categories=categories,
    )
    db.add(offer)
    db.flush()

    for product in included_products:
        db.add(OfferProduct(offer_id=offer.id, product_id=product.id, is_excluded=False))
    for product in excluded_products:
        db.add(OfferProduct(offer_id=offer.id, product_id=product.id, is_excluded=True))

    db.commit()
    return get_offer_by_id(db, offer.id)


def update_offer(db: Session, offer_id: int, offer_in: OfferUpdate) -> Offer:
    offer = get_offer_by_id(db, offer_id)
    update_data = offer_in.model_dump(exclude_unset=True)

    if "name" in update_data:
        offer.name = update_data["name"]
    if "description" in update_data:
        offer.description = update_data["description"]
    if "discount_percentage" in update_data:
        offer.discount_percentage = update_data["discount_percentage"]
    if "scope" in update_data:
        offer.scope = update_data["scope"]
    if "start_date" in update_data:
        offer.start_date = update_data["start_date"]
    if "end_date" in update_data:
        offer.end_date = update_data["end_date"]
    if "is_active" in update_data:
        offer.is_active = update_data["is_active"]
    if "category_ids" in update_data:
        offer.categories = _require_categories(db, update_data["category_ids"])

    if "included_product_ids" in update_data or "excluded_product_ids" in update_data:
        current_included = {link.product_id for link in offer.product_links if not link.is_excluded}
        current_excluded = {link.product_id for link in offer.product_links if link.is_excluded}
        included_ids = update_data.get("included_product_ids", list(current_included))
        excluded_ids = update_data.get("excluded_product_ids", list(current_excluded))

        if set(included_ids) & set(excluded_ids):
            raise BadRequestException("a product cannot be both included and excluded")

        included_products = _require_products(db, included_ids)
        excluded_products = _require_products(db, excluded_ids)

        db.query(OfferProduct).filter(OfferProduct.offer_id == offer.id).delete(synchronize_session=False)
        db.flush()

        for product in included_products:
            db.add(OfferProduct(offer_id=offer.id, product_id=product.id, is_excluded=False))
        for product in excluded_products:
            db.add(OfferProduct(offer_id=offer.id, product_id=product.id, is_excluded=True))

    db.commit()
    return get_offer_by_id(db, offer.id)


def delete_offer(db: Session, offer_id: int) -> None:
    offer = get_offer_by_id(db, offer_id)
    db.delete(offer)
    db.commit()


def get_active_offers(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    offers = (
        db.query(Offer)
        .filter(Offer.is_active.is_(True), Offer.start_date <= now, Offer.end_date >= now)
        .order_by(Offer.discount_percentage.desc())
        .all()
    )
    return {"data": offers, "count": len(offers)}
