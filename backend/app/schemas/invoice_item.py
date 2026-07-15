"""
InvoiceItem Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)


class InvoiceItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)


class InvoiceItemResponse(BaseModel):
    id: int
    invoice_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
