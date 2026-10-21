"""Business logic and calculations for order management."""

import uuid
from typing import Dict, Tuple
from src.models import OrderCreateRequest, OrderResponse, OrderStatus

TAX_RATE = 0.08  # 8% standard tax
DISCOUNT_RULES: Dict[str, float] = {
    "WELCOME10": 0.10,
    "VIP20": 0.20,
    "SUPER50": 0.50,
}


class OrderProcessingError(Exception):
    """Base exception for order processing."""
    pass


class InvalidDiscountError(OrderProcessingError):
    """Raised when an unrecognized discount code is used."""
    pass


class OrderService:
    def __init__(self):
        self._orders_db: Dict[str, OrderResponse] = {}

    def calculate_totals(
        self, subtotal: float, discount_code: str | None
    ) -> Tuple[float, float, float]:
        """Calculates discount amount, tax, and final total."""
        discount_rate = 0.0
        if discount_code:
            discount_code = discount_code.upper()
            if discount_code not in DISCOUNT_RULES:
                raise InvalidDiscountError(f"Discount code '{discount_code}' is invalid or expired.")
            discount_rate = DISCOUNT_RULES[discount_code]

        discount_amount = round(subtotal * discount_rate, 2)
        taxable_amount = max(0.0, subtotal - discount_amount)
        tax_amount = round(taxable_amount * TAX_RATE, 2)
        total_amount = round(taxable_amount + tax_amount, 2)

        return discount_amount, tax_amount, total_amount

    def create_order(self, request: OrderCreateRequest) -> OrderResponse:
        """Processes and stores a new order."""
        subtotal = round(
            sum(item.quantity * item.unit_price for item in request.items), 2
        )
        discount_amount, tax_amount, total_amount = self.calculate_totals(
            subtotal, request.discount_code
        )

        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        order = OrderResponse(
            order_id=order_id,
            customer_id=request.customer_id,
            items=request.items,
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status=OrderStatus.APPROVED if total_amount < 10000 else OrderStatus.PENDING,
        )
        self._orders_db[order_id] = order
        return order

    def get_order(self, order_id: str) -> OrderResponse | None:
        """Retrieves an order by ID."""
        return self._orders_db.get(order_id)
