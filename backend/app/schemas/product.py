"""
Product Pydantic schemas.
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# ProductCreate
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    name: str = Field(..., max_length=100)
    category: str | None = Field(default=None, max_length=100)
    sku: str = Field(..., max_length=50)
    barcode: str | None = Field(default=None, max_length=100)
    cost_price: Decimal
    selling_price: Decimal
    current_stock: int = 0
    minimum_stock: int = 0
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Product name cannot be empty or whitespace only")
            return trimmed
        return v

    @field_validator("category", "sku", "barcode", "image_url", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


# ---------------------------------------------------------------------------
# ProductUpdate
# ---------------------------------------------------------------------------

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    sku: str | None = Field(default=None, max_length=50)
    barcode: str | None = Field(default=None, max_length=100)
    cost_price: Decimal | None = None
    selling_price: Decimal | None = None
    current_stock: int | None = None
    minimum_stock: int | None = None
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Product name cannot be empty or whitespace only")
            return trimmed
        return v

    @field_validator("category", "sku", "barcode", "image_url", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


# ---------------------------------------------------------------------------
# Product Response
# ---------------------------------------------------------------------------

class ProductResponse(BaseModel):
    id: int
    business_id: int
    name: str
    category: str | None
    sku: str
    barcode: str | None
    cost_price: Decimal
    selling_price: Decimal
    current_stock: int
    minimum_stock: int
    image_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# ---------------------------------------------------------------------------
# Paginated Response
# ---------------------------------------------------------------------------

class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(
        cls,
        items: list[ProductResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "ProductListResponse":
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )