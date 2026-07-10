"""
Customer Pydantic schemas.

Normalization rules applied here:
- name: stripped of leading/trailing whitespace; empty/whitespace-only rejected; max 100 after trim
- phone: stripped; empty string converted to None
- email: lowercased and stripped; empty string converted to None; validated as EmailStr when supplied
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_phone(v: Any) -> Any:
    """Strip phone string; convert empty string to None."""
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return v


def _normalize_email(v: Any) -> Any:
    """Lowercase and strip email; convert empty string to None."""
    if isinstance(v, str):
        v = v.strip().lower()
        return v if v else None
    return v


# ---------------------------------------------------------------------------
# CustomerCreate
# ---------------------------------------------------------------------------

class CustomerCreate(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Customer name cannot be empty or whitespace only")
            return trimmed
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: Any) -> Any:
        return _normalize_phone(v)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        return _normalize_email(v)


# ---------------------------------------------------------------------------
# CustomerUpdate  (all fields optional — uses model_fields_set semantics)
# ---------------------------------------------------------------------------

class CustomerUpdate(BaseModel):
    """
    Partial update schema.

    Only fields present in model_fields_set are applied to the ORM object.
    - Omitted field  → leave existing DB value unchanged
    - Explicit null  → clear the nullable field (allowed for phone and email)
    - name cannot be set to None
    """
    name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Customer name cannot be empty or whitespace only")
            return trimmed
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: Any) -> Any:
        return _normalize_phone(v)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        return _normalize_email(v)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CustomerResponse(BaseModel):
    id: int
    business_id: int
    name: str
    phone: str | None
    email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Paginated list response
# ---------------------------------------------------------------------------

class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(
        cls,
        items: list[CustomerResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "CustomerListResponse":
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
