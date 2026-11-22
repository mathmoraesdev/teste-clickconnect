"""Repositórios em memória."""

from decimal import Decimal

from ..models.catalog import Product, Store
from ..models.orders import Order

PRODUCTS = [
    Product(
        "p1",
        "Smartphone Aurora 128GB",
        'Tela 6.5", 128GB',
        Decimal("1899.90"),
        "Celulares",
    ),
    Product(
        "p2",
        "Fone Bluetooth Pulse",
        "Cancelamento de ruído",
        Decimal("299.90"),
        "Áudio",
    ),
    Product(
        "p3",
        "Notebook Nimbus 14",
        "i5, 16GB, SSD 512GB",
        Decimal("3799.00"),
        "Informática",
    ),
    Product(
        "p4",
        "Mouse Sem Fio Glide",
        "Ergonômico, 2.4GHz",
        Decimal("89.90"),
        "Informática",
    ),
    Product("p5", 'Smart TV 50" 4K', "LED, HDR, 3 HDMI", Decimal("2499.00"), "TV"),
    Product("p6", "Cafeteira Express", "15 bar, 1,2L", Decimal("349.90"), "Casa"),
]

STORES = [
    Store("s1", "MegaLoja Centro", "Rua Principal, 100 - Centro", -29.7600, -51.1470),
    Store(
        "s2",
        "MegaLoja Shopping Norte",
        "Av. das Nações, 2500 - Norte",
        -29.7200,
        -51.1300,
    ),
    Store("s3", "MegaLoja Zona Sul", "Av. Sul, 800 - Zona Sul", -29.8000, -51.1600),
]

STOCK = {
    ("s1", "p1"): 5,
    ("s1", "p2"): 20,
    ("s1", "p3"): 2,
    ("s1", "p4"): 30,
    ("s1", "p5"): 0,
    ("s1", "p6"): 8,
    ("s2", "p1"): 0,
    ("s2", "p2"): 10,
    ("s2", "p3"): 6,
    ("s2", "p4"): 15,
    ("s2", "p5"): 3,
    ("s2", "p6"): 0,
    ("s3", "p1"): 3,
    ("s3", "p2"): 0,
    ("s3", "p3"): 0,
    ("s3", "p4"): 5,
    ("s3", "p5"): 4,
    ("s3", "p6"): 12,
}


class CatalogRepository:
    def __init__(self) -> None:
        self._products = {p.id: p for p in PRODUCTS}
        self._stores = {s.id: s for s in STORES}

    def list_products(
        self, q: str | None = None, category: str | None = None
    ) -> list[Product]:
        items = list(self._products.values())
        if q:
            items = [p for p in items if q.lower() in p.name.lower()]
        if category:
            items = [p for p in items if p.category.lower() == category.lower()]
        return items

    def get_product(self, product_id: str) -> Product | None:
        return self._products.get(product_id)

    def list_stores(self) -> list[Store]:
        return list(self._stores.values())

    def get_store(self, store_id: str) -> Store | None:
        return self._stores.get(store_id)


class OrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._seq = 0

    def next_id(self) -> str:
        self._seq += 1
        return f"PED-{self._seq:06d}"

    def save(self, order: Order) -> Order:
        self._orders[order.id] = order
        return order

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def list(self) -> list[Order]:
        return list(self._orders.values())

    def find_by_pickup_code(self, store_id: str, code: str) -> Order | None:
        code = code.strip().upper()
        for o in self._orders.values():
            if o.pickup.store_id == store_id and (
                o.pickup.code == code or o.id == code
            ):
                return o
        return None
