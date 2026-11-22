from .integrations.erp import FakeERP
from .integrations.notifications import FakeNotificationService
from .integrations.payment import FakePaymentGateway
from .repositories.memory import STOCK, CatalogRepository, OrderRepository
from .services.orders import OrderService

catalog = CatalogRepository()
erp = FakeERP(STOCK)
notifier = FakeNotificationService()
service = OrderService(catalog, OrderRepository(), erp, FakePaymentGateway(), notifier)


def get_catalog() -> CatalogRepository:
    return catalog


def get_service() -> OrderService:
    return service
