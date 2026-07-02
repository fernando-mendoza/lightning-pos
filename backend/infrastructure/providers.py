"""Singletons de servicios externos, compartidos entre routers.

En test mode (LPOS_TEST_MODE=1) se sustituyen por fakes deterministicos.
El estado del FakeLightningService (invoices emitidos/pagados) debe ser
compartido entre pos.py, webhooks.py y las rutas de testing — por eso las
instancias viven aqui y no en cada router.
"""
from config import settings

if settings.test_mode:
    from infrastructure.exchange.fake_exchange_client import FakeExchangeClient
    from infrastructure.lnbits.fake_lightning_service import FakeLightningService

    exchange_service = FakeExchangeClient()
    lightning_service = FakeLightningService()
else:
    from infrastructure.exchange.bitso_client import BitsoClient
    from infrastructure.lnbits.lnbits_client import LNbitsClient

    exchange_service = BitsoClient()
    lightning_service = LNbitsClient()
