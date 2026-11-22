import math
import secrets
from decimal import Decimal

from ..integrations.erp import FakeERP, InsufficientStock
from ..integrations.notifications import FakeNotificationService
from ..integrations.payment import FakePaymentGateway
from ..models.orders import (
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    Pickup,
    utcnow,
)
from ..repositories.memory import CatalogRepository, OrderRepository
from ..schemas.api import OrderIn

STATUS_LABELS = {
    OrderStatus.PENDING: "Aguardando pagamento",
    OrderStatus.CONFIRMED: "Pagamento confirmado, aguardando separação",
    OrderStatus.PREPARING: "Em separação",
    OrderStatus.READY: "Pronto para retirada",
    OrderStatus.COMPLETED: "Retirado",
    OrderStatus.CANCELLED: "Cancelado",
}

ALLOWED = {
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
}


class NotFound(Exception): ...


class BusinessError(Exception): ...


class PaymentDeclined(Exception): ...


def _distance_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


class OrderService:
    def __init__(
        self,
        catalog: CatalogRepository,
        orders: OrderRepository,
        erp: FakeERP,
        gateway: FakePaymentGateway,
        notifier: FakeNotificationService,
    ):
        self.catalog, self.orders, self.erp = catalog, orders, erp
        self.gateway, self.notifier = gateway, notifier

    def pickup_options(
        self, items: dict[str, int], lat: float | None, lng: float | None
    ):
        for pid in items:
            if not self.catalog.get_product(pid):
                raise NotFound(f"Produto {pid} não encontrado")
        result = []
        for s in self.catalog.list_stores():
            missing = [
                pid for pid, q in items.items() if self.erp.available(s.id, pid) < q
            ]
            dist = (
                _distance_km(lat, lng, s.lat, s.lng)
                if lat is not None and lng is not None
                else None
            )
            result.append(
                {
                    "store": s,
                    "can_fulfill": not missing,
                    "missing": missing,
                    "distance_km": dist,
                }
            )
        ok = [r for r in result if r["can_fulfill"]]
        if ok:
            best = min(
                ok, key=lambda r: (r["distance_km"] is None, r["distance_km"] or 0)
            )
            best["recommended"] = True
        result.sort(
            key=lambda r: (
                not r["can_fulfill"],
                r["distance_km"] if r["distance_km"] is not None else 0,
            )
        )
        return result

    def create_order(self, data: OrderIn) -> Order:
        store = self.catalog.get_store(data.store_id)
        if not store:
            raise NotFound("Loja não encontrada")
        qty: dict[str, int] = {}
        for it in data.items:
            qty[it.product_id] = qty.get(it.product_id, 0) + it.quantity
        items, total = [], Decimal(0)
        for pid, q in qty.items():
            p = self.catalog.get_product(pid)
            if not p:
                raise NotFound(f"Produto {pid} não encontrado")
            items.append(OrderItem(p.id, p.name, q, p.price))
            total += p.price * q

        try:
            self.erp.reserve(store.id, qty)
        except InsufficientStock as e:
            raise BusinessError(
                f"Produto {e.product_id} indisponível na loja {store.name}"
            ) from e

        result = self.gateway.charge(total, data.payment.method, data.payment.token)
        if not result.approved:
            self.erp.release(store.id, qty)
            raise PaymentDeclined(result.reason or "Pagamento recusado")

        order = Order(
            id=self.orders.next_id(),
            customer=Customer(
                data.customer.name, data.customer.email, data.customer.phone
            ),
            items=items,
            total=total,
            status=OrderStatus.CONFIRMED,
            pickup=Pickup(store_id=store.id, code=secrets.token_hex(3).upper()),
            payment=Payment(
                data.payment.method,
                PaymentStatus.APPROVED,
                result.transaction_id,
                total,
            ),
        )
        self.orders.save(order)
        self.notifier.send(
            order.id,
            "order_confirmed",
            order.customer.email,
            f"Compra {order.id} confirmada. Retirada na {store.name}. Código: {order.pickup.code}",
        )
        return order

    def get(self, order_id: str) -> Order:
        o = self.orders.get(order_id)
        if not o:
            raise NotFound("Pedido não encontrado")
        return o

    def list_by_email(self, email: str) -> list[Order]:
        return [
            o for o in self.orders.list() if o.customer.email.lower() == email.lower()
        ]

    def list_by_store(
        self, store_id: str, status: OrderStatus | None = None
    ) -> list[Order]:
        if not self.catalog.get_store(store_id):
            raise NotFound("Loja não encontrada")
        res = [o for o in self.orders.list() if o.pickup.store_id == store_id]
        if status:
            res = [o for o in res if o.status == status]
        return res

    def _transition(self, order: Order, new: OrderStatus) -> Order:
        if new not in ALLOWED.get(order.status, set()):
            raise BusinessError(
                f"Não é possível passar de '{STATUS_LABELS[order.status]}' para '{STATUS_LABELS[new]}'"
            )
        order.status = new
        return order

    def start_preparing(self, order_id: str) -> Order:
        return self._transition(self.get(order_id), OrderStatus.PREPARING)

    def mark_ready(self, order_id: str) -> Order:
        o = self._transition(self.get(order_id), OrderStatus.READY)
        o.pickup.ready_at = utcnow()
        store = self.catalog.get_store(o.pickup.store_id)
        self.notifier.send(
            o.id,
            "order_ready",
            o.customer.email,
            f"Seu pedido {o.id} está pronto na {store.name}. Código de retirada: {o.pickup.code}",
        )
        return o

    def validate_and_deliver(self, store_id: str, code: str) -> Order:
        o = self.orders.find_by_pickup_code(store_id, code)
        if not o:
            raise NotFound("Código inválido para esta loja")
        self._transition(o, OrderStatus.COMPLETED)
        o.pickup.picked_up_at = utcnow()
        self.erp.commit(store_id, {i.product_id: i.quantity for i in o.items})
        return o

    def cancel(self, order_id: str) -> Order:
        o = self.get(order_id)
        self._transition(o, OrderStatus.CANCELLED)
        self.erp.release(o.pickup.store_id, {i.product_id: i.quantity for i in o.items})
        return o
