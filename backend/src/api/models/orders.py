from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum


def utcnow() -> datetime:
    return datetime.now(UTC)


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    APPROVED = "approved"
    DECLINED = "declined"


@dataclass
class Customer:
    name: str
    email: str
    phone: str


@dataclass
class OrderItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal


@dataclass
class Payment:
    method: str
    status: PaymentStatus
    transaction_id: str | None
    amount: Decimal


@dataclass
class Pickup:
    store_id: str
    code: str
    ready_at: datetime | None = None
    picked_up_at: datetime | None = None


@dataclass
class Order:
    id: str
    customer: Customer
    items: list[OrderItem]
    total: Decimal
    status: OrderStatus
    pickup: Pickup
    payment: Payment
    created_at: datetime = field(default_factory=utcnow)
