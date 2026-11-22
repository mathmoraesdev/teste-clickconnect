from .models.orders import Order
from .schemas.api import OrderItemOut, OrderOut, PaymentOut, StoreOut


def order_out(o: Order, catalog) -> OrderOut:
    s = catalog.get_store(o.pickup.store_id)
    return OrderOut(
        id=o.id,
        status=o.status,
        customer_name=o.customer.name,
        customer_email=o.customer.email,
        store=StoreOut(id=s.id, name=s.name, address=s.address),
        items=[OrderItemOut(**vars(i)) for i in o.items],
        total=o.total,
        payment=PaymentOut(
            method=o.payment.method,
            status=o.payment.status.value,
            transaction_id=o.payment.transaction_id,
            amount=o.payment.amount,
        ),
        pickup_code=o.pickup.code,
        created_at=o.created_at,
        ready_at=o.pickup.ready_at,
        picked_up_at=o.pickup.picked_up_at,
    )
