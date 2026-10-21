"""FastAPI Order Processing API Gateway."""

from fastapi import FastAPI, HTTPException, status
from src.models import OrderCreateRequest, OrderResponse
from src.service import OrderService, InvalidDiscountError

app = FastAPI(
    title="Enterprise Order Service",
    version="1.0.0",
    description="Microservice demonstrating AI-integrated enterprise SDLC pipeline",
)

order_service = OrderService()


@app.get("/health", tags=["System"])
def health_check():
    """Liveness and readiness probe for Kubernetes / Azure Container Apps."""
    return {"status": "HEALTHY", "version": "1.0.0"}


@app.post(
    "/api/v1/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Orders"],
)
def create_order(request: OrderCreateRequest):
    """Creates a new order with pricing, validation, and tax calculation."""
    try:
        return order_service.create_order(request)
    except InvalidDiscountError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal processing failure: {str(exc)}",
        )


@app.get(
    "/api/v1/orders/{order_id}",
    response_model=OrderResponse,
    tags=["Orders"],
)
def get_order(order_id: str):
    """Fetches details for a specific order."""
    order = order_service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found.",
        )
    return order
