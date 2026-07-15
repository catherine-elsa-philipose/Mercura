"""
StockAdjustment Pydantic schemas.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# StockAdjustmentCreate
# ---------------------------------------------------------------------------

class StockAdjustmentCreate(BaseModel):
    adjustment_type: Literal["IN", "OUT", "ADJUSTMENT"]
    quantity: int
    reason: str | None = Field(default=None, max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, v: Any) -> Any:
        if isinstance(v, str):
            trimmed = v.strip()
            return trimmed if trimmed else None
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v == 0:
            raise ValueError("Quantity cannot be zero")
        return v

    @model_validator(mode="after")
    def validate_type_and_quantity(self) -> "StockAdjustmentCreate":
        if self.adjustment_type == "IN" and self.quantity <= 0:
            raise ValueError("Quantity must be positive for 'IN' adjustments")
        if self.adjustment_type == "OUT" and self.quantity >= 0:
            raise ValueError("Quantity must be negative for 'OUT' adjustments")
        return self


# ---------------------------------------------------------------------------
# StockAdjustmentResponse
# ---------------------------------------------------------------------------

class StockAdjustmentResponse(BaseModel):
    id: int
    business_id: int
    product_id: int
    adjustment_type: str
    quantity: int
    reason: str | None
    created_by: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


# ---------------------------------------------------------------------------
# Paginated Response
# ---------------------------------------------------------------------------

class StockAdjustmentListResponse(BaseModel):
    items: list[StockAdjustmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(
        cls,
        items: list[StockAdjustmentResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "StockAdjustmentListResponse":
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
