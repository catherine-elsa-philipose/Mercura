from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator

class BusinessCreate(BaseModel):
    name: str = Field(..., max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Business name cannot be empty or whitespace only")
            return trimmed
        return v

class BusinessResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class BusinessWithRoleResponse(BaseModel):
    id: int
    name: str
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
