from fastapi import APIRouter, Depends, HTTPException

from ..deps import catalog, get_service, notifier
from ..mappers import order_out
from ..schemas.api import NotificationOut, OrderIn, OrderOut, OrderStatusOut
from ..services.orders import (
    STATUS_LABELS,
    BusinessError,
    NotFound,
    OrderService,
    PaymentDeclined,
)

router = APIRouter(prefix="/api/v1/orders", tags=["pedidos"])


def _run(fn, *a):
    try:
        return fn(*a)
    except NotFound as e:
        raise HTTPException(404, str(e))
    except PaymentDeclined as e:
        raise HTTPException(402, str(e))
    except BusinessError as e:
        raise HTTPException(409, str(e))


@router.post("", response_model=OrderOut, status_code=201)
def create_order(body: OrderIn, svc: OrderService = Depends(get_service)):
    return order_out(_run(svc.create_order, body), catalog)


@router.get("", response_model=list[OrderOut])
def list_orders(email: str, svc: OrderService = Depends(get_service)):
    return [order_out(o, catalog) for o in svc.list_by_email(email)]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, svc: OrderService = Depends(get_service)):
    return order_out(_run(svc.get, order_id), catalog)


@router.get("/{order_id}/status", response_model=OrderStatusOut)
def get_status(order_id: str, svc: OrderService = Depends(get_service)):
    o = _run(svc.get, order_id)
    return OrderStatusOut(id=o.id, status=o.status, label=STATUS_LABELS[o.status])


@router.get("/{order_id}/notifications", response_model=list[NotificationOut])
def get_notifications(order_id: str, svc: OrderService = Depends(get_service)):
    _run(svc.get, order_id)
    return [NotificationOut(**vars(n)) for n in notifier.for_order(order_id)]


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: str, svc: OrderService = Depends(get_service)):
    return order_out(_run(svc.cancel, order_id), catalog)


@router.post("/{order_id}/start-preparing", response_model=OrderOut)
def start_preparing(order_id: str, svc: OrderService = Depends(get_service)):
    return order_out(_run(svc.start_preparing, order_id), catalog)


@router.post("/{order_id}/ready", response_model=OrderOut)
def ready(order_id: str, svc: OrderService = Depends(get_service)):
    return order_out(_run(svc.mark_ready, order_id), catalog)
