"""
Dashboard & Analytics Pydantic schemas.

All response schemas are read-only aggregations of business data.
No write operations are defined here.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared building-block schemas
# ---------------------------------------------------------------------------

class RevenuePoint(BaseModel):
    """A single labelled revenue data point (e.g. one day, one week)."""
    label: str
    revenue: Decimal
    invoice_count: int

    model_config = {"from_attributes": True}


class TopCustomerResponse(BaseModel):
    customer_id: int
    customer_name: str
    total_spend: Decimal
    invoice_count: int

    model_config = {"from_attributes": True}


class TopProductResponse(BaseModel):
    product_id: int
    product_name: str
    sku: str
    total_quantity_sold: int
    total_revenue: Decimal

    model_config = {"from_attributes": True}


class LowStockProductResponse(BaseModel):
    product_id: int
    product_name: str
    sku: str
    current_stock: int
    minimum_stock: int

    model_config = {"from_attributes": True}


class RecentActivityResponse(BaseModel):
    """One event in the recent-activity feed."""
    activity_type: str          # e.g. "new_invoice", "payment", "stock_adjustment"
    description: str
    occurred_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoint 1 – /dashboard/summary
# ---------------------------------------------------------------------------

class DashboardSummaryResponse(BaseModel):
    # Customers
    total_customers: int
    active_customers: int
    inactive_customers: int

    # Products
    total_products: int
    active_products: int
    inactive_products: int
    low_stock_products: int
    out_of_stock_products: int

    # Invoices
    total_invoices: int
    paid_invoices: int
    unpaid_invoices: int
    partially_paid_invoices: int
    cancelled_invoices: int

    # Payments / Revenue
    total_payments: int
    today_revenue: Decimal
    monthly_revenue: Decimal
    outstanding_balance: Decimal


# ---------------------------------------------------------------------------
# Endpoint 2 – /dashboard/sales
# ---------------------------------------------------------------------------

class SalesAnalyticsResponse(BaseModel):
    start_date: date | None
    end_date: date | None

    daily_revenue: list[RevenuePoint]
    weekly_revenue: list[RevenuePoint]
    monthly_revenue: list[RevenuePoint]
    yearly_revenue: list[RevenuePoint]

    invoice_count: int
    payment_count: int
    average_invoice_value: Decimal
    average_payment_value: Decimal
    highest_invoice: Decimal
    lowest_invoice: Decimal


# ---------------------------------------------------------------------------
# Endpoint 3 – /dashboard/inventory
# ---------------------------------------------------------------------------

class InventoryAnalyticsResponse(BaseModel):
    total_inventory_items: int
    total_inventory_quantity: int
    inventory_cost_value: Decimal
    inventory_selling_value: Decimal
    potential_profit: Decimal

    low_stock_list: list[LowStockProductResponse]
    out_of_stock_list: list[LowStockProductResponse]
    recent_stock_adjustments: list[RecentActivityResponse]


# ---------------------------------------------------------------------------
# Endpoint 4 – /dashboard/customers
# ---------------------------------------------------------------------------

class CustomerAnalyticsResponse(BaseModel):
    total_customers: int
    active_customers: int
    inactive_customers: int
    new_customers_this_month: int

    highest_spending_customers: list[TopCustomerResponse]
    average_customer_spend: Decimal
    average_invoice_count_per_customer: Decimal


# ---------------------------------------------------------------------------
# Endpoint 5 – /dashboard/products
# ---------------------------------------------------------------------------

class ProductAnalyticsResponse(BaseModel):
    top_selling_products: list[TopProductResponse]
    lowest_selling_products: list[TopProductResponse]
    highest_revenue_products: list[TopProductResponse]
    average_selling_price: Decimal


# ---------------------------------------------------------------------------
# Endpoint 6 – /dashboard/finance
# ---------------------------------------------------------------------------

class FinanceAnalyticsResponse(BaseModel):
    total_revenue: Decimal
    total_outstanding_balance: Decimal
    payments_received: Decimal
    average_payment: Decimal
    average_invoice_value: Decimal
    tax_collected: Decimal
    discount_given: Decimal


# ---------------------------------------------------------------------------
# Endpoint 7 – /dashboard/activity
# ---------------------------------------------------------------------------

class ActivityResponse(BaseModel):
    activities: list[RecentActivityResponse]
    total: int