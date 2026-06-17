from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.dashboard import service
from app.features.dashboard.schemas import (
    CustomerGrowthResponse,
    DashboardStatsResponse,
    LowStockAlertsResponse,
    OrdersByCategoryResponse,
    RevenueOverviewResponse,
    SalesDistributionResponse,
    TopProductsResponse,
    WeeklySalesResponse,
)

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_dashboard_stats(db)


@router.get("/charts/revenue-overview", response_model=RevenueOverviewResponse)
def get_revenue_overview(
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_revenue_overview(db, year)


@router.get("/charts/orders-by-category", response_model=OrdersByCategoryResponse)
def get_orders_by_category(
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_orders_by_category(db, year)


@router.get("/charts/sales-distribution", response_model=SalesDistributionResponse)
def get_sales_distribution(
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_sales_distribution(db, year)


@router.get("/charts/customer-growth", response_model=CustomerGrowthResponse)
def get_customer_growth(
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_customer_growth(db, year)


@router.get("/charts/weekly-sales", response_model=WeeklySalesResponse)
def get_weekly_sales(
    target_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_weekly_sales(db, target_date)


@router.get("/charts/top-products", response_model=TopProductsResponse)
def get_top_products(
    limit: int = Query(6, ge=1, le=50),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_top_products(db, limit)


@router.get("/charts/low-stock-alerts", response_model=LowStockAlertsResponse)
def get_low_stock_alerts(
    reorder_threshold: int = Query(10, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_low_stock_alerts(db, reorder_threshold, limit)
