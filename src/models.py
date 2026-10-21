"""Domain models for Order Processing Service."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FULFILLED = "FULFILLED"


class OrderItem(BaseModel):
    sku: str = Field(..., min_length=3, max_length=50, description="Stock Keeping Unit")
    quantity: int = Field(..., gt=0, description="Quantity of items")
    unit_price: float = Field(..., gt=0.0, description="Price per unit in USD")


class OrderCreateRequest(BaseModel):
    customer_id: str = Field(..., min_length=3, description="Unique customer identifier")
    items: List[OrderItem] = Field(..., min_length=1, description="List of items in order")
    discount_code: Optional[str] = Field(None, max_length=20, description="Optional discount code")

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[OrderItem]) -> List[OrderItem]:
        if not v:
            raise ValueError("Order must contain at least one item")
        return v


class OrderResponse(BaseModel):
    order_id: str
    customer_id: str
    items: List[OrderItem]
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    status: OrderStatus
