"""
Payment Pydantic schemas.
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.payment import PaymentMethod


class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod
    reference: str | None = Field(default=None, max_length=100)

    @field_validator("reference", mode="before")
    @classmethod
    def trim_reference(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class PaymentResponse(BaseModel):
    id: int
    business_id: int
    invoice_id: int
    amount: Decimal
    payment_method: PaymentMethod
    reference: str | None
    paid_at: datetime

    model_config = {
        "from_attributes": True
    }


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(
        cls,
        items: list[PaymentResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaymentListResponse":
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
