"""Notificações simuladas, guardadas em memória."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Notification:
    order_id: str
    kind: str
    channel: str
    to: str
    message: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FakeNotificationService:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def send(
        self, order_id: str, kind: str, to: str, message: str, channel: str = "email"
    ) -> None:
        self.sent.append(Notification(order_id, kind, channel, to, message))

    def for_order(self, order_id: str) -> list[Notification]:
        return [n for n in self.sent if n.order_id == order_id]
