"""
Invoice Pydantic schemas.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.invoice import InvoiceStatus
from app.schemas.invoice_item import InvoiceItemCreate, InvoiceItemResponse


class InvoiceCreate(BaseModel):
    customer_id: int
    tax: Decimal = Field(default=Decimal("0.00"), ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: str | None = Field(default=None, max_length=500)
    invoice_date: date | None = None
    due_date: date | None = None
    items: list[InvoiceItemCreate] = Field(default_factory=list)

    @field_validator("notes", mode="before")
    @classmethod
    def trim_notes(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class InvoiceUpdate(BaseModel):
    customer_id: int | None = None
    tax: Decimal | None = Field(default=None, ge=0)
    discount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)
    invoice_date: date | None = None
    due_date: date | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def trim_notes(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class InvoiceResponse(BaseModel):
    id: int
    business_id: int
    customer_id: int
    invoice_number: str
    status: InvoiceStatus
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal
    notes: str | None
    invoice_date: date | None
    due_date: date | None
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemResponse]

    model_config = {
        "from_attributes": True
    }


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(
        cls,
        items: list[InvoiceResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "InvoiceListResponse":
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
