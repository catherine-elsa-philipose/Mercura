"""
Dashboard & Analytics API routes.
All endpoints are READ-ONLY aggregations scoped to the authenticated business.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.dependencies import get_db
from app.models.business_member import BusinessMember
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment
from app.schemas.dashboard import (
    ActivityResponse,
    CustomerAnalyticsResponse,
    DashboardSummaryResponse,
    FinanceAnalyticsResponse,
    InventoryAnalyticsResponse,
    LowStockProductResponse,
    ProductAnalyticsResponse,
    RecentActivityResponse,
    RevenuePoint,
    SalesAnalyticsResponse,
    TopCustomerResponse,
    TopProductResponse,
)

router = APIRouter()

ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# Endpoint 1 – Summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_summary(
    business_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    # ── Customers ──────────────────────────────────────────────────────────
    cust_counts = (
        db.query(
            func.count(Customer.id).label("total"),
            func.sum(case((Customer.is_active == True, 1), else_=0)).label("active"),
            func.sum(case((Customer.is_active == False, 1), else_=0)).label("inactive"),
        )
        .filter(Customer.business_id == business_id)
        .one()
    )

    # ── Products ───────────────────────────────────────────────────────────
    prod_counts = (
        db.query(
            func.count(Product.id).label("total"),
            func.sum(case((Product.is_active == True, 1), else_=0)).label("active"),
            func.sum(case((Product.is_active == False, 1), else_=0)).label("inactive"),
            func.sum(
                case((Product.current_stock < Product.minimum_stock, 1), else_=0)
            ).label("low_stock"),
            func.sum(
                case((Product.current_stock == 0, 1), else_=0)
            ).label("out_of_stock"),
        )
        .filter(Product.business_id == business_id)
        .one()
    )

    # ── Invoices ───────────────────────────────────────────────────────────
    inv_counts = (
        db.query(
            func.count(Invoice.id).label("total"),
            func.sum(case((Invoice.status == InvoiceStatus.PAID, 1), else_=0)).label("paid"),
            func.sum(case((Invoice.status == InvoiceStatus.UNPAID, 1), else_=0)).label("unpaid"),
            func.sum(case((Invoice.status == InvoiceStatus.PARTIALLY_PAID, 1), else_=0)).label("partially_paid"),
            func.sum(case((Invoice.status == InvoiceStatus.CANCELLED, 1), else_=0)).label("cancelled"),
        )
        .filter(Invoice.business_id == business_id)
        .one()
    )

    # ── Revenue ────────────────────────────────────────────────────────────
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    pay_total = (
        db.query(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), ZERO))
        .filter(Payment.business_id == business_id)
        .one()
    )

    today_rev = (
        db.query(func.coalesce(func.sum(Payment.amount), ZERO))
        .filter(
            Payment.business_id == business_id,
            func.date(Payment.paid_at) == today,
        )
        .scalar()
    )

    month_rev = (
        db.query(func.coalesce(func.sum(Payment.amount), ZERO))
        .filter(
            Payment.business_id == business_id,
            func.date(Payment.paid_at) >= month_start,
        )
        .scalar()
    )

    # Outstanding = sum of totals for UNPAID + PARTIALLY_PAID invoices minus payments already made on them
    outstanding_invoices = (
        db.query(func.coalesce(func.sum(Invoice.total), ZERO))
        .filter(
            Invoice.business_id == business_id,
            Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIALLY_PAID]),
        )
        .scalar()
    )
    payments_on_outstanding = (
        db.query(func.coalesce(func.sum(Payment.amount), ZERO))
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .filter(
            Payment.business_id == business_id,
            Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIALLY_PAID]),
        )
        .scalar()
    )
    outstanding_balance = Decimal(str(outstanding_invoices)) - Decimal(str(payments_on_outstanding))

    return DashboardSummaryResponse(
        total_customers=cust_counts.total or 0,
        active_customers=cust_counts.active or 0,
        inactive_customers=cust_counts.inactive or 0,
        total_products=prod_counts.total or 0,
        active_products=prod_counts.active or 0,
        inactive_products=prod_counts.inactive or 0,
        low_stock_products=prod_counts.low_stock or 0,
        out_of_stock_products=prod_counts.out_of_stock or 0,
        total_invoices=inv_counts.total or 0,
        paid_invoices=inv_counts.paid or 0,
        unpaid_invoices=inv_counts.unpaid or 0,
        partially_paid_invoices=inv_counts.partially_paid or 0,
        cancelled_invoices=inv_counts.cancelled or 0,
        total_payments=pay_total[0] or 0,
        today_revenue=Decimal(str(today_rev)),
        monthly_revenue=Decimal(str(month_rev)),
        outstanding_balance=outstanding_balance,
    )


# ---------------------------------------------------------------------------
# Endpoint 2 – Sales analytics
# ---------------------------------------------------------------------------

@router.get("/sales", response_model=SalesAnalyticsResponse)
def get_sales(
    business_id: int,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    pay_q = db.query(Payment).filter(Payment.business_id == business_id)
    inv_q = db.query(Invoice).filter(Invoice.business_id == business_id)

    if start_date:
        pay_q = pay_q.filter(func.date(Payment.paid_at) >= start_date)
        inv_q = inv_q.filter(Invoice.invoice_date >= start_date)
    if end_date:
        pay_q = pay_q.filter(func.date(Payment.paid_at) <= end_date)
        inv_q = inv_q.filter(Invoice.invoice_date <= end_date)

    # Aggregates
    pay_agg = pay_q.with_entities(
        func.count(Payment.id),
        func.coalesce(func.sum(Payment.amount), ZERO),
        func.coalesce(func.avg(Payment.amount), ZERO),
    ).one()

    inv_agg = inv_q.filter(Invoice.status != InvoiceStatus.CANCELLED).with_entities(
        func.count(Invoice.id),
        func.coalesce(func.avg(Invoice.total), ZERO),
        func.coalesce(func.max(Invoice.total), ZERO),
        func.coalesce(func.min(Invoice.total), ZERO),
    ).one()

    # Daily revenue (last 30 days or filtered range)
    daily_rows = (
        pay_q.with_entities(
            func.date(Payment.paid_at).label("day"),
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("cnt"),
        )
        .group_by(func.date(Payment.paid_at))
        .order_by(func.date(Payment.paid_at))
        .all()
    )
    daily_revenue = [
        RevenuePoint(label=str(r.day), revenue=Decimal(str(r.revenue)), invoice_count=r.cnt)
        for r in daily_rows
    ]

    # Weekly revenue
    weekly_rows = (
        pay_q.with_entities(
            func.to_char(Payment.paid_at, "IYYY-IW").label("week"),
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("cnt"),
        )
        .group_by(func.to_char(Payment.paid_at, "IYYY-IW"))
        .order_by(func.to_char(Payment.paid_at, "IYYY-IW"))
        .all()
    )
    weekly_revenue = [
        RevenuePoint(label=r.week, revenue=Decimal(str(r.revenue)), invoice_count=r.cnt)
        for r in weekly_rows
    ]

    # Monthly revenue
    monthly_rows = (
        pay_q.with_entities(
            func.to_char(Payment.paid_at, "YYYY-MM").label("month"),
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("cnt"),
        )
        .group_by(func.to_char(Payment.paid_at, "YYYY-MM"))
        .order_by(func.to_char(Payment.paid_at, "YYYY-MM"))
        .all()
    )
    monthly_revenue = [
        RevenuePoint(label=r.month, revenue=Decimal(str(r.revenue)), invoice_count=r.cnt)
        for r in monthly_rows
    ]

    # Yearly revenue
    yearly_rows = (
        pay_q.with_entities(
            func.to_char(Payment.paid_at, "YYYY").label("year"),
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("cnt"),
        )
        .group_by(func.to_char(Payment.paid_at, "YYYY"))
        .order_by(func.to_char(Payment.paid_at, "YYYY"))
        .all()
    )
    yearly_revenue = [
        RevenuePoint(label=r.year, revenue=Decimal(str(r.revenue)), invoice_count=r.cnt)
        for r in yearly_rows
    ]

    return SalesAnalyticsResponse(
        start_date=start_date,
        end_date=end_date,
        daily_revenue=daily_revenue,
        weekly_revenue=weekly_revenue,
        monthly_revenue=monthly_revenue,
        yearly_revenue=yearly_revenue,
        invoice_count=inv_agg[0] or 0,
        payment_count=pay_agg[0] or 0,
        average_invoice_value=Decimal(str(inv_agg[1])),
        average_payment_value=Decimal(str(pay_agg[2])),
        highest_invoice=Decimal(str(inv_agg[2])),
        lowest_invoice=Decimal(str(inv_agg[3])),
    )


# ---------------------------------------------------------------------------
# Endpoint 3 – Inventory analytics
# ---------------------------------------------------------------------------

@router.get("/inventory", response_model=InventoryAnalyticsResponse)
def get_inventory(
    business_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    inv_agg = (
        db.query(
            func.count(Product.id),
            func.coalesce(func.sum(Product.current_stock), 0),
            func.coalesce(func.sum(Product.current_stock * Product.cost_price), ZERO),
            func.coalesce(func.sum(Product.current_stock * Product.selling_price), ZERO),
        )
        .filter(Product.business_id == business_id, Product.is_active == True)
        .one()
    )

    low_stock_rows = (
        db.query(Product)
        .filter(
            Product.business_id == business_id,
            Product.is_active == True,
            Product.current_stock < Product.minimum_stock,
            Product.current_stock > 0,
        )
        .order_by(Product.current_stock.asc())
        .limit(20)
        .all()
    )
    out_of_stock_rows = (
        db.query(Product)
        .filter(
            Product.business_id == business_id,
            Product.is_active == True,
            Product.current_stock == 0,
        )
        .order_by(Product.name.asc())
        .limit(20)
        .all()
    )

    recent_adj = (
        db.query(StockAdjustment)
        .filter(StockAdjustment.business_id == business_id)
        .order_by(StockAdjustment.created_at.desc())
        .limit(20)
        .all()
    )

    cost_val = Decimal(str(inv_agg[2]))
    sell_val = Decimal(str(inv_agg[3]))

    return InventoryAnalyticsResponse(
        total_inventory_items=inv_agg[0] or 0,
        total_inventory_quantity=inv_agg[1] or 0,
        inventory_cost_value=cost_val,
        inventory_selling_value=sell_val,
        potential_profit=sell_val - cost_val,
        low_stock_list=[
            LowStockProductResponse(
                product_id=p.id, product_name=p.name, sku=p.sku,
                current_stock=p.current_stock, minimum_stock=p.minimum_stock,
            )
            for p in low_stock_rows
        ],
        out_of_stock_list=[
            LowStockProductResponse(
                product_id=p.id, product_name=p.name, sku=p.sku,
                current_stock=p.current_stock, minimum_stock=p.minimum_stock,
            )
            for p in out_of_stock_rows
        ],
        recent_stock_adjustments=[
            RecentActivityResponse(
                activity_type="stock_adjustment",
                description=f"{a.adjustment_type} {abs(a.quantity)} units — {a.reason or 'No reason'}",
                occurred_at=a.created_at,
            )
            for a in recent_adj
        ],
    )


# ---------------------------------------------------------------------------
# Endpoint 4 – Customer analytics
# ---------------------------------------------------------------------------

@router.get("/customers", response_model=CustomerAnalyticsResponse)
def get_customer_analytics(
    business_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    cust_counts = (
        db.query(
            func.count(Customer.id).label("total"),
            func.sum(case((Customer.is_active == True, 1), else_=0)).label("active"),
            func.sum(case((Customer.is_active == False, 1), else_=0)).label("inactive"),
        )
        .filter(Customer.business_id == business_id)
        .one()
    )

    month_start = datetime.utcnow().date().replace(day=1)
    new_this_month = (
        db.query(func.count(Customer.id))
        .filter(
            Customer.business_id == business_id,
            func.date(Customer.created_at) >= month_start,
        )
        .scalar()
    )

    # Top spenders: join customers -> invoices -> payments (PAID invoices only)
    top_rows = (
        db.query(
            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
            func.coalesce(func.sum(Payment.amount), ZERO).label("total_spend"),
            func.count(func.distinct(Invoice.id)).label("invoice_count"),
        )
        .outerjoin(Invoice, (Invoice.customer_id == Customer.id) & (Invoice.business_id == business_id))
        .outerjoin(Payment, (Payment.invoice_id == Invoice.id) & (Payment.business_id == business_id))
        .filter(Customer.business_id == business_id)
        .group_by(Customer.id, Customer.name)
        .order_by(func.coalesce(func.sum(Payment.amount), ZERO).desc())
        .limit(10)
        .all()
    )

    avg_spend = (
        db.query(func.coalesce(func.avg(Payment.amount), ZERO))
        .filter(Payment.business_id == business_id)
        .scalar()
    )

    total_customers = cust_counts.total or 1
    avg_inv_per_customer = Decimal(str(
        db.query(func.count(Invoice.id)).filter(Invoice.business_id == business_id).scalar() or 0
    )) / Decimal(str(total_customers))

    return CustomerAnalyticsResponse(
        total_customers=cust_counts.total or 0,
        active_customers=cust_counts.active or 0,
        inactive_customers=cust_counts.inactive or 0,
        new_customers_this_month=new_this_month or 0,
        highest_spending_customers=[
            TopCustomerResponse(
                customer_id=r.customer_id,
                customer_name=r.customer_name,
                total_spend=Decimal(str(r.total_spend)),
                invoice_count=r.invoice_count,
            )
            for r in top_rows
        ],
        average_customer_spend=Decimal(str(avg_spend)),
        average_invoice_count_per_customer=avg_inv_per_customer,
    )


# ---------------------------------------------------------------------------
# Endpoint 5 – Product analytics
# ---------------------------------------------------------------------------

@router.get("/products", response_model=ProductAnalyticsResponse)
def get_product_analytics(
    business_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    # Products with quantity sold via paid invoices
    sold_rows = (
        db.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku.label("sku"),
            func.coalesce(func.sum(InvoiceItem.quantity), 0).label("total_qty"),
            func.coalesce(func.sum(InvoiceItem.line_total), ZERO).label("total_revenue"),
        )
        .outerjoin(InvoiceItem, InvoiceItem.product_id == Product.id)
        .outerjoin(
            Invoice,
            (Invoice.id == InvoiceItem.invoice_id)
            & (Invoice.status == InvoiceStatus.PAID)
            & (Invoice.business_id == business_id),
        )
        .filter(Product.business_id == business_id)
        .group_by(Product.id, Product.name, Product.sku)
        .all()
    )

    # Sort for different views
    by_qty_desc = sorted(sold_rows, key=lambda r: r.total_qty, reverse=True)
    by_qty_asc = sorted(sold_rows, key=lambda r: r.total_qty)
    by_rev_desc = sorted(sold_rows, key=lambda r: r.total_revenue, reverse=True)

    def _to_schema(r) -> TopProductResponse:
        return TopProductResponse(
            product_id=r.product_id,
            product_name=r.product_name,
            sku=r.sku,
            total_quantity_sold=r.total_qty,
            total_revenue=Decimal(str(r.total_revenue)),
        )

    avg_price = (
        db.query(func.coalesce(func.avg(Product.selling_price), ZERO))
        .filter(Product.business_id == business_id, Product.is_active == True)
        .scalar()
    )

    return ProductAnalyticsResponse(
        top_selling_products=[_to_schema(r) for r in by_qty_desc[:10]],
        lowest_selling_products=[_to_schema(r) for r in by_qty_asc[:10]],
        highest_revenue_products=[_to_schema(r) for r in by_rev_desc[:10]],
        average_selling_price=Decimal(str(avg_price)),
    )


# ---------------------------------------------------------------------------
# Endpoint 6 – Finance analytics
# ---------------------------------------------------------------------------

@router.get("/finance", response_model=FinanceAnalyticsResponse)
def get_finance(
    business_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    pay_agg = (
        db.query(
            func.coalesce(func.sum(Payment.amount), ZERO),
            func.coalesce(func.avg(Payment.amount), ZERO),
        )
        .filter(Payment.business_id == business_id)
        .one()
    )

    inv_agg = (
        db.query(
            func.coalesce(func.avg(Invoice.total), ZERO),
            func.coalesce(func.sum(Invoice.tax), ZERO),
            func.coalesce(func.sum(Invoice.discount), ZERO),
        )
        .filter(
            Invoice.business_id == business_id,
            Invoice.status != InvoiceStatus.CANCELLED,
        )
        .one()
    )

    outstanding_invoices = (
        db.query(func.coalesce(func.sum(Invoice.total), ZERO))
        .filter(
            Invoice.business_id == business_id,
            Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIALLY_PAID]),
        )
        .scalar()
    )
    payments_on_outstanding = (
        db.query(func.coalesce(func.sum(Payment.amount), ZERO))
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .filter(
            Payment.business_id == business_id,
            Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIALLY_PAID]),
        )
        .scalar()
    )
    outstanding_balance = Decimal(str(outstanding_invoices)) - Decimal(str(payments_on_outstanding))

    return FinanceAnalyticsResponse(
        total_revenue=Decimal(str(pay_agg[0])),
        total_outstanding_balance=outstanding_balance,
        payments_received=Decimal(str(pay_agg[0])),
        average_payment=Decimal(str(pay_agg[1])),
        average_invoice_value=Decimal(str(inv_agg[0])),
        tax_collected=Decimal(str(inv_agg[1])),
        discount_given=Decimal(str(inv_agg[2])),
    )


# ---------------------------------------------------------------------------
# Endpoint 7 – Recent activity feed
# ---------------------------------------------------------------------------

@router.get("/activity", response_model=ActivityResponse)
def get_activity(
    business_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    activities: list[RecentActivityResponse] = []

    # New customers
    for c in (
        db.query(Customer)
        .filter(Customer.business_id == business_id)
        .order_by(Customer.created_at.desc())
        .limit(limit)
        .all()
    ):
        activities.append(RecentActivityResponse(
            activity_type="new_customer",
            description=f"New customer added: {c.name}",
            occurred_at=c.created_at,
        ))

    # New invoices
    for inv in (
        db.query(Invoice)
        .filter(Invoice.business_id == business_id)
        .order_by(Invoice.created_at.desc())
        .limit(limit)
        .all()
    ):
        activities.append(RecentActivityResponse(
            activity_type="new_invoice",
            description=f"Invoice {inv.invoice_number} — {inv.status.value} — total {inv.total}",
            occurred_at=inv.created_at,
        ))

    # Payments
    for pay in (
        db.query(Payment)
        .filter(Payment.business_id == business_id)
        .order_by(Payment.paid_at.desc())
        .limit(limit)
        .all()
    ):
        activities.append(RecentActivityResponse(
            activity_type="payment",
            description=f"Payment of {pay.amount} via {pay.payment_method.value}",
            occurred_at=pay.paid_at,
        ))

    # Stock adjustments
    for adj in (
        db.query(StockAdjustment)
        .filter(StockAdjustment.business_id == business_id)
        .order_by(StockAdjustment.created_at.desc())
        .limit(limit)
        .all()
    ):
        activities.append(RecentActivityResponse(
            activity_type="stock_adjustment",
            description=f"Stock {adj.adjustment_type}: {abs(adj.quantity)} units — {adj.reason or 'No reason'}",
            occurred_at=adj.created_at,
        ))

    # New products
    for prod in (
        db.query(Product)
        .filter(Product.business_id == business_id)
        .order_by(Product.created_at.desc())
        .limit(limit)
        .all()
    ):
        activities.append(RecentActivityResponse(
            activity_type="new_product",
            description=f"New product added: {prod.name} (SKU: {prod.sku})",
            occurred_at=prod.created_at,
        ))

    # Sort all by newest first and truncate
    activities.sort(key=lambda a: a.occurred_at, reverse=True)
    activities = activities[:limit]

    return ActivityResponse(activities=activities, total=len(activities))