from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.core.utils import calculate_percentage_change
from app.features.products.models import ProductReview
from app.features.products import service as products_service
from app.features.reviews.schemas import (
    MyReviewListResponse,
    MyReviewResponse,
    ReviewAnalyticsMetric,
    ReviewAnalyticsResponse,
    ReviewListResponse,
    ReviewResponse,
    ReviewVisibilityUpdate,
)


def _to_review_response(review: ProductReview) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        product_id=review.product_id,
        product_name=review.product.name,
        user_id=review.user_id,
        customer_name=review.user.full_name,
        rating=review.rating,
        comment=review.comment,
        is_hidden=review.is_hidden,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def get_my_reviews(db: Session, user_id: int) -> MyReviewListResponse:
    reviews = (
        db.query(ProductReview)
        .filter(ProductReview.user_id == user_id)
        .order_by(ProductReview.created_at.desc())
        .all()
    )

    data = [
        MyReviewResponse(
            id=review.id,
            product_id=review.product_id,
            product_name=review.product.name,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
        for review in reviews
    ]
    return MyReviewListResponse(data=data, count=len(data))


def get_reviews(
    db: Session,
    page: int = 1,
    limit: int = 10,
    product_id: Optional[int] = None,
    rating: Optional[int] = None,
    is_hidden: Optional[bool] = None,
) -> ReviewListResponse:
    query = db.query(ProductReview)

    if product_id is not None:
        query = query.filter(ProductReview.product_id == product_id)
    if rating is not None:
        query = query.filter(ProductReview.rating == rating)
    if is_hidden is not None:
        query = query.filter(ProductReview.is_hidden.is_(is_hidden))

    total_count = query.count()

    offset = (page - 1) * limit
    reviews = query.order_by(ProductReview.created_at.desc()).offset(offset).limit(limit).all()

    data = [_to_review_response(review) for review in reviews]
    return ReviewListResponse(data=data, count=total_count)


def set_review_visibility(db: Session, review_id: int, visibility_in: ReviewVisibilityUpdate) -> ReviewResponse:
    review = db.query(ProductReview).filter(ProductReview.id == review_id).first()
    if not review:
        raise NotFoundException("Review not found")

    review.is_hidden = visibility_in.is_hidden
    db.commit()

    products_service.recalculate_product_rating(db, review.product_id)
    db.refresh(review)

    return _to_review_response(review)




def _bucket_products_by_rating(reviews: list[tuple[int, int]]) -> tuple[int, int, int]:
    ratings_by_product = defaultdict(list)
    for product_id, rating in reviews:
        ratings_by_product[product_id].append(rating)

    bad_count = 0
    good_count = 0
    for ratings in ratings_by_product.values():
        average = (sum(Decimal(rating) for rating in ratings) / Decimal(len(ratings))).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        if average <= 3:
            bad_count += 1
        else:
            good_count += 1

    return len(ratings_by_product), bad_count, good_count


def get_reviews_analytics(db: Session) -> ReviewAnalyticsResponse:
    period_start = datetime.now(timezone.utc) - timedelta(days=30)

    all_reviews = db.query(ProductReview.product_id, ProductReview.rating, ProductReview.created_at).all()
    previous_reviews = [review for review in all_reviews if review.created_at and review.created_at < period_start]

    current_total_reviews = len(all_reviews)
    previous_total_reviews = len(previous_reviews)

    current_reviewed, current_bad, current_good = _bucket_products_by_rating(
        [(review.product_id, review.rating) for review in all_reviews]
    )
    previous_reviewed, previous_bad, previous_good = _bucket_products_by_rating(
        [(review.product_id, review.rating) for review in previous_reviews]
    )

    return ReviewAnalyticsResponse(
        total_reviews=ReviewAnalyticsMetric(
            value=current_total_reviews,
            change_percentage=calculate_percentage_change(current_total_reviews, previous_total_reviews),
        ),
        total_products_reviewed=ReviewAnalyticsMetric(
            value=current_reviewed,
            change_percentage=calculate_percentage_change(current_reviewed, previous_reviewed),
        ),
        products_with_bad_reviews=ReviewAnalyticsMetric(
            value=current_bad,
            change_percentage=calculate_percentage_change(current_bad, previous_bad),
        ),
        products_with_good_reviews=ReviewAnalyticsMetric(
            value=current_good,
            change_percentage=calculate_percentage_change(current_good, previous_good),
        ),
    )
