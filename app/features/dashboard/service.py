from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session, selectinload

from app.features.categories.models import Category
from app.features.orders.models import Order, OrderItem, OrderStatus
from app.features.products.models import Product
from app.features.shipments.models import Shipment
from app.features.users.models import User, UserType
from app.core.money import to_decimal
from app.core.utils import calculate_percentage_change
from app.features.dashboard.schemas import (
    CustomerGrowthItem,
    CustomerGrowthResponse,
    DashboardMetric,
    DashboardStatsResponse,
    LowStockAlertItem,
    LowStockAlertsResponse,
    OrdersByCategoryItem,
    OrdersByCategoryResponse,
    RevenueOverviewItem,
    RevenueOverviewResponse,
    SalesDistributionItem,
    SalesDistributionResponse,
    TopProductItem,
    TopProductsResponse,
    WeeklySalesItem,
    WeeklySalesResponse,
)


MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _money(value) -> Decimal:
    return to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _percentage(value) -> Decimal:
    return to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _period_start(days: int = 30) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _date_range_for_year(year: int) -> tuple[datetime, datetime]:
    return datetime(year, 1, 1, tzinfo=timezone.utc), datetime(year + 1, 1, 1, tzinfo=timezone.utc)


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _get_revenue_created_at(order: Order) -> datetime | None:
    delivered_dates = [
        _as_aware(shipment.delivered_at)
        for shipment in order.shipments
        if shipment.delivered_at is not None
    ]
    if delivered_dates:
        return max(delivered_dates)
    return _as_aware(order.updated_at or order.created_at)


def _delivered_order_options():
    return (
        selectinload(Order.shipments),
        selectinload(Order.items)
        .joinedload(OrderItem.product)
        .joinedload(Product.category),
    )


def _get_delivered_orders(db: Session) -> list[Order]:
    return (
        db.query(Order)
        .options(*_delivered_order_options())
        .filter(Order.status == OrderStatus.DELIVERED)
        .all()
    )


def _order_expense(order: Order) -> Decimal:
    return _money(
        sum(
            (
                to_decimal(item.product.cost_price if item.product else 0) * Decimal(item.quantity)
                for item in order.items
            ),
            Decimal("0"),
        )
    )


def _customer_count_query(db: Session):
    return db.query(User).filter(User.user_type == UserType.CUSTOMER.value)


def get_dashboard_stats(db: Session) -> DashboardStatsResponse:
    period_start = _period_start()
    previous_period_start = period_start - timedelta(days=30)

    orders = db.query(Order).all()
    delivered_orders = [order for order in orders if order.status == OrderStatus.DELIVERED]
    current_orders = [order for order in orders if order.created_at and _as_aware(order.created_at) >= period_start]
    previous_orders = [
        order
        for order in orders
        if order.created_at and previous_period_start <= _as_aware(order.created_at) < period_start
    ]
    current_delivered = [
        order for order in delivered_orders if order.created_at and _as_aware(order.created_at) >= period_start
    ]
    previous_delivered = [
        order
        for order in delivered_orders
        if order.created_at and previous_period_start <= _as_aware(order.created_at) < period_start
    ]

    total_revenue = _money(sum((to_decimal(order.total_amount) for order in delivered_orders), Decimal("0")))
    current_revenue = _money(sum((to_decimal(order.total_amount) for order in current_delivered), Decimal("0")))
    previous_revenue = _money(sum((to_decimal(order.total_amount) for order in previous_delivered), Decimal("0")))

    total_customers = _customer_count_query(db).count()
    current_customers = _customer_count_query(db).filter(User.created_at >= period_start).count()
    previous_customers = _customer_count_query(db).filter(
        User.created_at >= previous_period_start,
        User.created_at < period_start,
    ).count()

    total_products = db.query(Product).filter(Product.is_active.is_(True)).count()
    current_products = db.query(Product).filter(Product.is_active.is_(True), Product.created_at >= period_start).count()
    previous_products = db.query(Product).filter(
        Product.is_active.is_(True),
        Product.created_at >= previous_period_start,
        Product.created_at < period_start,
    ).count()

    avg_order_value = _money(total_revenue / Decimal(len(delivered_orders)) if delivered_orders else 0)
    current_avg_order_value = _money(current_revenue / Decimal(len(current_delivered)) if current_delivered else 0)
    previous_avg_order_value = _money(previous_revenue / Decimal(len(previous_delivered)) if previous_delivered else 0)

    customers_with_orders = db.query(func.count(distinct(Order.user_id))).scalar() or 0
    current_customers_with_orders = (
        db.query(func.count(distinct(Order.user_id)))
        .filter(Order.created_at >= period_start)
        .scalar()
        or 0
    )
    previous_customers_with_orders = (
        db.query(func.count(distinct(Order.user_id)))
        .filter(Order.created_at >= previous_period_start, Order.created_at < period_start)
        .scalar()
        or 0
    )
    conversion_rate = _percentage(Decimal(customers_with_orders) / Decimal(total_customers) * Decimal("100") if total_customers else 0)
    current_conversion_rate = _percentage(
        Decimal(current_customers_with_orders) / Decimal(current_customers) * Decimal("100")
        if current_customers
        else 0
    )
    previous_conversion_rate = _percentage(
        Decimal(previous_customers_with_orders) / Decimal(previous_customers) * Decimal("100")
        if previous_customers
        else 0
    )

    return DashboardStatsResponse(
        totalRevenue=DashboardMetric(
            value=total_revenue,
            change_percentage=calculate_percentage_change(current_revenue, previous_revenue),
        ),
        totalOrders=DashboardMetric(
            value=len(orders),
            change_percentage=calculate_percentage_change(Decimal(len(current_orders)), Decimal(len(previous_orders))),
        ),
        totalCustomers=DashboardMetric(
            value=total_customers,
            change_percentage=calculate_percentage_change(Decimal(current_customers), Decimal(previous_customers)),
        ),
        totalProducts=DashboardMetric(
            value=total_products,
            change_percentage=calculate_percentage_change(Decimal(current_products), Decimal(previous_products)),
        ),
        avgOrderValue=DashboardMetric(
            value=avg_order_value,
            change_percentage=calculate_percentage_change(current_avg_order_value, previous_avg_order_value),
        ),
        conversionRate=DashboardMetric(
            value=conversion_rate,
            change_percentage=calculate_percentage_change(current_conversion_rate, previous_conversion_rate),
        ),
    )


def get_revenue_overview(db: Session, year: int) -> RevenueOverviewResponse:
    start, end = _date_range_for_year(year)
    monthly = {
        month: {"revenue": Decimal("0"), "expenses": Decimal("0")}
        for month in range(1, 13)
    }

    for order in _get_delivered_orders(db):
        revenue_date = _get_revenue_created_at(order)
        if not revenue_date or revenue_date < start or revenue_date >= end:
            continue
        month_values = monthly[revenue_date.month]
        month_values["revenue"] += to_decimal(order.total_amount)
        month_values["expenses"] += _order_expense(order)

    data = [
        RevenueOverviewItem(
            month=MONTH_LABELS[month - 1],
            revenue=_money(values["revenue"]),
            expenses=_money(values["expenses"]),
            profit=_money(values["revenue"] - values["expenses"]),
        )
        for month, values in monthly.items()
    ]
    return RevenueOverviewResponse(year=year, data=data)


def get_orders_by_category(db: Session, year: int) -> OrdersByCategoryResponse:
    start, end = _date_range_for_year(year)
    category_data: dict[tuple[int | None, str], dict[str, Decimal | set[int]]] = defaultdict(
        lambda: {"orders": set(), "revenue": Decimal("0")}
    )

    for order in _get_delivered_orders(db):
        revenue_date = _get_revenue_created_at(order)
        if not revenue_date or revenue_date < start or revenue_date >= end:
            continue
        for item in order.items:
            product = item.product
            category = product.category if product else None
            key = (category.id if category else None, category.name if category else "Uncategorized")
            category_data[key]["orders"].add(order.id)
            category_data[key]["revenue"] += to_decimal(item.unit_price) * Decimal(item.quantity)

    data = [
        OrdersByCategoryItem(
            category_id=category_id,
            category=category,
            orders=len(values["orders"]),
            revenue=_money(values["revenue"]),
        )
        for (category_id, category), values in category_data.items()
    ]
    data.sort(key=lambda item: item.revenue, reverse=True)
    return OrdersByCategoryResponse(year=year, data=data)


def get_sales_distribution(db: Session, year: int) -> SalesDistributionResponse:
    orders_by_category = get_orders_by_category(db, year).data
    total_revenue = sum((to_decimal(item.revenue) for item in orders_by_category), Decimal("0"))

    data = [
        SalesDistributionItem(
            category_id=item.category_id,
            category=item.category,
            revenue=_money(item.revenue),
            percentage=_percentage(to_decimal(item.revenue) / total_revenue * Decimal("100") if total_revenue else 0),
        )
        for item in orders_by_category
    ]
    return SalesDistributionResponse(year=year, data=data)


def get_customer_growth(db: Session, year: int) -> CustomerGrowthResponse:
    start, end = _date_range_for_year(year)
    new_customers_by_month = {month: 0 for month in range(1, 13)}
    returning_customers_by_month = {month: set() for month in range(1, 13)}

    customers = _customer_count_query(db).all()
    for customer in customers:
        created_at = _as_aware(customer.created_at)
        if created_at and start <= created_at < end:
            new_customers_by_month[created_at.month] += 1

    orders = db.query(Order).filter(Order.created_at >= start, Order.created_at < end).all()
    first_order_dates = dict(
        db.query(Order.user_id, func.min(Order.created_at))
        .group_by(Order.user_id)
        .all()
    )
    for order in orders:
        order_created_at = _as_aware(order.created_at)
        first_order_at = _as_aware(first_order_dates.get(order.user_id))
        if not order_created_at or not first_order_at:
            continue
        if first_order_at < datetime(order_created_at.year, order_created_at.month, 1, tzinfo=timezone.utc):
            returning_customers_by_month[order_created_at.month].add(order.user_id)

    data = [
        CustomerGrowthItem(
            month=MONTH_LABELS[month - 1],
            newCustomers=new_customers_by_month[month],
            returningCustomers=len(returning_customers_by_month[month]),
        )
        for month in range(1, 13)
    ]
    return CustomerGrowthResponse(year=year, data=data)


def get_weekly_sales(db: Session, target_date: date | None = None) -> WeeklySalesResponse:
    selected_date = target_date or datetime.now(timezone.utc).date()
    week_start_date = selected_date - timedelta(days=selected_date.weekday())
    week_end_date = week_start_date + timedelta(days=6)
    week_start = datetime.combine(week_start_date, time.min, tzinfo=timezone.utc)
    week_end_exclusive = datetime.combine(week_end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    daily = {index: {"revenue": Decimal("0"), "orders": 0} for index in range(7)}

    for order in _get_delivered_orders(db):
        revenue_date = _get_revenue_created_at(order)
        if not revenue_date or revenue_date < week_start or revenue_date >= week_end_exclusive:
            continue
        values = daily[revenue_date.weekday()]
        values["revenue"] += to_decimal(order.total_amount)
        values["orders"] += 1

    data = [
        WeeklySalesItem(
            day=DAY_LABELS[index],
            revenue=_money(values["revenue"]),
            orders=int(values["orders"]),
        )
        for index, values in daily.items()
    ]
    return WeeklySalesResponse(
        weekStart=week_start_date.isoformat(),
        weekEnd=week_end_date.isoformat(),
        data=data,
    )


def get_top_products(db: Session, limit: int = 6) -> TopProductsResponse:
    period_start = _period_start()
    previous_period_start = period_start - timedelta(days=30)
    product_data = defaultdict(
        lambda: {
            "product": None,
            "revenue": Decimal("0"),
            "sales": 0,
            "current_revenue": Decimal("0"),
            "previous_revenue": Decimal("0"),
        }
    )

    for order in _get_delivered_orders(db):
        revenue_date = _get_revenue_created_at(order)
        for item in order.items:
            product = item.product
            if not product:
                continue
            item_revenue = to_decimal(item.unit_price) * Decimal(item.quantity)
            values = product_data[product.id]
            values["product"] = product
            values["revenue"] += item_revenue
            values["sales"] += item.quantity
            if revenue_date and revenue_date >= period_start:
                values["current_revenue"] += item_revenue
            elif revenue_date and previous_period_start <= revenue_date < period_start:
                values["previous_revenue"] += item_revenue

    ranked = sorted(product_data.values(), key=lambda values: values["revenue"], reverse=True)[:limit]
    data = []
    for index, values in enumerate(ranked, start=1):
        product = values["product"]
        data.append(
            TopProductItem(
                rank=index,
                product_id=product.id,
                name=product.name,
                sku=product.sku,
                category=product.category.name if product.category else None,
                revenue=_money(values["revenue"]),
                sales=int(values["sales"]),
                stock=product.stock_quantity,
                change_percentage=calculate_percentage_change(
                    _money(values["current_revenue"]),
                    _money(values["previous_revenue"]),
                ),
            )
        )
    return TopProductsResponse(data=data, count=len(data))


def get_low_stock_alerts(db: Session, reorder_threshold: int = 10, limit: int = 10) -> LowStockAlertsResponse:
    products = (
        db.query(Product)
        .options(selectinload(Product.category))
        .filter(Product.is_active.is_(True), Product.stock_quantity <= reorder_threshold)
        .order_by(Product.stock_quantity.asc(), Product.name.asc())
        .limit(limit)
        .all()
    )

    data = []
    for product in products:
        stock_percentage = _percentage(
            Decimal(product.stock_quantity) / Decimal(reorder_threshold) * Decimal("100")
            if reorder_threshold
            else 0
        )
        if stock_percentage <= Decimal("30"):
            severity = "Critical"
        elif stock_percentage <= Decimal("60"):
            severity = "Low"
        else:
            severity = "Fair"
        data.append(
            LowStockAlertItem(
                product_id=product.id,
                name=product.name,
                sku=product.sku,
                category=product.category.name if product.category else None,
                stock=product.stock_quantity,
                reorderThreshold=reorder_threshold,
                severity=severity,
                stockPercentage=stock_percentage,
            )
        )
    return LowStockAlertsResponse(data=data, count=len(data))
