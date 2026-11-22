from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from ..models.orders import OrderStatus


class ProductOut(BaseModel):
    id: str
    name: str
    description: str
    price: Decimal
    category: str


class StoreOut(BaseModel):
    id: str
    name: str
    address: str


class AvailabilityOut(BaseModel):
    product_id: str
    store_id: str
    quantity: int


class ProductAvailabilityOut(BaseModel):
    store: StoreOut
    quantity: int


class CartItemIn(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, le=50)


class PickupOptionsIn(BaseModel):
    items: list[CartItemIn] = Field(min_length=1)
    lat: float | None = None
    lng: float | None = None


class PickupOptionOut(BaseModel):
    store: StoreOut
    can_fulfill: bool
    missing: list[str]
    distance_km: float | None = None
    recommended: bool = False


class CustomerIn(BaseModel):
    name: str = Field(min_length=2)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = Field(min_length=8)


class PaymentIn(BaseModel):
    method: str = Field(pattern="^(card|pix)$")
    token: str | None = None


class OrderIn(BaseModel):
    customer: CustomerIn
    store_id: str
    items: list[CartItemIn] = Field(min_length=1)
    payment: PaymentIn


class OrderItemOut(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal


class PaymentOut(BaseModel):
    method: str
    status: str
    transaction_id: str | None
    amount: Decimal


class OrderOut(BaseModel):
    id: str
    status: OrderStatus
    customer_name: str
    customer_email: str
    store: StoreOut
    items: list[OrderItemOut]
    total: Decimal
    payment: PaymentOut
    pickup_code: str
    created_at: datetime
    ready_at: datetime | None
    picked_up_at: datetime | None


class OrderStatusOut(BaseModel):
    id: str
    status: OrderStatus
    label: str


class ValidateCodeIn(BaseModel):
    code: str = Field(min_length=3)


class NotificationOut(BaseModel):
    kind: str
    channel: str
    to: str
    message: str
    sent_at: datetime
