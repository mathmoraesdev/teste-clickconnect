from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Product:
    id: str
    name: str
    description: str
    price: Decimal
    category: str


@dataclass
class Store:
    id: str
    name: str
    address: str
    lat: float
    lng: float
