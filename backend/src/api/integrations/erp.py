"""ERP simulado."""

from threading import Lock


class InsufficientStock(Exception):
    def __init__(self, product_id: str, store_id: str):
        super().__init__(f"Estoque insuficiente de {product_id} na loja {store_id}")
        self.product_id = product_id
        self.store_id = store_id


class FakeERP:
    def __init__(self, balances: dict[tuple[str, str], int]):
        self._balance = dict(balances)
        self._reserved: dict[tuple[str, str], int] = {}
        self._lock = Lock()

    def available(self, store_id: str, product_id: str) -> int:
        key = (store_id, product_id)
        return self._balance.get(key, 0) - self._reserved.get(key, 0)

    def reserve(self, store_id: str, items: dict[str, int]) -> None:
        """Reserva todos os itens ou nenhum."""
        with self._lock:
            for pid, qty in items.items():
                if self.available(store_id, pid) < qty:
                    raise InsufficientStock(pid, store_id)
            for pid, qty in items.items():
                key = (store_id, pid)
                self._reserved[key] = self._reserved.get(key, 0) + qty

    def release(self, store_id: str, items: dict[str, int]) -> None:
        with self._lock:
            for pid, qty in items.items():
                key = (store_id, pid)
                self._reserved[key] = max(0, self._reserved.get(key, 0) - qty)

    def commit(self, store_id: str, items: dict[str, int]) -> None:
        """Baixa definitiva do estoque."""
        with self._lock:
            for pid, qty in items.items():
                key = (store_id, pid)
                self._reserved[key] = max(0, self._reserved.get(key, 0) - qty)
                self._balance[key] = max(0, self._balance.get(key, 0) - qty)
