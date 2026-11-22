from fastapi import APIRouter, Depends, HTTPException

from ..deps import catalog, erp, get_catalog, get_service
from ..mappers import order_out
from ..models.orders import OrderStatus
from ..repositories.memory import CatalogRepository
from ..schemas.api import (
    AvailabilityOut,
    OrderOut,
    PickupOptionOut,
    PickupOptionsIn,
    StoreOut,
    ValidateCodeIn,
)
from ..services.orders import BusinessError, NotFound, OrderService

router = APIRouter(prefix="/api/v1", tags=["lojas"])


@router.get("/stores", response_model=list[StoreOut])
def list_stores(c: CatalogRepository = Depends(get_catalog)):
    return [StoreOut(id=s.id, name=s.name, address=s.address) for s in c.list_stores()]


@router.get("/stores/{store_id}/availability", response_model=list[AvailabilityOut])
def store_availability(store_id: str, c: CatalogRepository = Depends(get_catalog)):
    if not c.get_store(store_id):
        raise HTTPException(404, "Loja não encontrada")
    return [
        AvailabilityOut(
            product_id=p.id, store_id=store_id, quantity=erp.available(store_id, p.id)
        )
        for p in c.list_products()
    ]


@router.post("/pickup/options", response_model=list[PickupOptionOut])
def pickup_options(body: PickupOptionsIn, svc: OrderService = Depends(get_service)):
    qty: dict[str, int] = {}
    for i in body.items:
        qty[i.product_id] = qty.get(i.product_id, 0) + i.quantity
    try:
        opts = svc.pickup_options(qty, body.lat, body.lng)
    except NotFound as e:
        raise HTTPException(404, str(e))
    return [
        PickupOptionOut(
            store=StoreOut(
                id=o["store"].id, name=o["store"].name, address=o["store"].address
            ),
            can_fulfill=o["can_fulfill"],
            missing=o["missing"],
            distance_km=o["distance_km"],
            recommended=o.get("recommended", False),
        )
        for o in opts
    ]


@router.get("/stores/{store_id}/orders", response_model=list[OrderOut])
def store_orders(
    store_id: str,
    status: OrderStatus | None = None,
    svc: OrderService = Depends(get_service),
):
    try:
        return [order_out(o, catalog) for o in svc.list_by_store(store_id, status)]
    except NotFound as e:
        raise HTTPException(404, str(e))


@router.post("/stores/{store_id}/pickup/validate", response_model=OrderOut)
def validate_pickup(
    store_id: str, body: ValidateCodeIn, svc: OrderService = Depends(get_service)
):
    try:
        return order_out(svc.validate_and_deliver(store_id, body.code), catalog)
    except NotFound as e:
        raise HTTPException(404, str(e))
    except BusinessError as e:
        raise HTTPException(409, str(e))
