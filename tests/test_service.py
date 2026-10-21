"""Unit tests for OrderService."""

import pytest
from src.models import OrderCreateRequest, OrderItem, OrderStatus
from src.service import OrderService, InvalidDiscountError


@pytest.fixture
def service():
    return OrderService()


def test_calculate_totals_without_discount(service):
    subtotal = 100.0
    discount, tax, total = service.calculate_totals(subtotal, None)
    assert discount == 0.0
    assert tax == 8.0  # 8% of 100
    assert total == 108.0


def test_calculate_totals_with_valid_discount(service):
    subtotal = 200.0
    discount, tax, total = service.calculate_totals(subtotal, "VIP20")
    assert discount == 40.0  # 20% of 200
    # Taxable: 160.0. Tax: 160 * 0.08 = 12.80
    assert tax == 12.80
    assert total == 172.80


def test_calculate_totals_invalid_discount_raises_error(service):
    with pytest.raises(InvalidDiscountError):
        service.calculate_totals(100.0, "INVALID_CODE")


def test_create_order_standard(service):
    req = OrderCreateRequest(
        customer_id="cust_12345",
        items=[
            OrderItem(sku="SKU-LAPTOP", quantity=1, unit_price=1200.0),
            OrderItem(sku="SKU-MOUSE", quantity=2, unit_price=25.0),
        ],
        discount_code="WELCOME10",
    )
    order = service.create_order(req)
    assert order.order_id.startswith("ord_")
    assert order.customer_id == "cust_12345"
    assert order.subtotal == 1250.0
    assert order.discount_amount == 125.0
    assert order.status == OrderStatus.APPROVED
