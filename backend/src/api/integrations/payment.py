"""Gateway de pagamento simulado."""

import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentResult:
    approved: bool
    transaction_id: str | None
    reason: str | None = None


class FakePaymentGateway:
    DECLINE_TOKEN = "recusado"

    def charge(self, amount: Decimal, method: str, token: str | None) -> PaymentResult:
        if token == self.DECLINE_TOKEN:
            return PaymentResult(False, None, "Pagamento recusado pelo emissor")
        return PaymentResult(True, f"TX-{uuid.uuid4().hex[:10].upper()}")
