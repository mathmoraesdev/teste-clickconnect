from fastapi import APIRouter, Depends, HTTPException

from ..deps import erp, get_catalog
from ..repositories.memory import CatalogRepository
from ..schemas.api import ProductAvailabilityOut, ProductOut, StoreOut

router = APIRouter(prefix="/api/v1/products", tags=["produtos"])


@router.get("", response_model=list[ProductOut])
def list_products(
    q: str | None = None,
    category: str | None = None,
    catalog: CatalogRepository = Depends(get_catalog),
):
    return [ProductOut(**vars(p)) for p in catalog.list_products(q, category)]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, catalog: CatalogRepository = Depends(get_catalog)):
    p = catalog.get_product(product_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    return ProductOut(**vars(p))


@router.get("/{product_id}/availability", response_model=list[ProductAvailabilityOut])
def product_availability(
    product_id: str, catalog: CatalogRepository = Depends(get_catalog)
):
    if not catalog.get_product(product_id):
        raise HTTPException(404, "Produto não encontrado")
    return [
        ProductAvailabilityOut(
            store=StoreOut(id=s.id, name=s.name, address=s.address),
            quantity=erp.available(s.id, product_id),
        )
        for s in catalog.list_stores()
    ]
