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
    from infrastructure.wallet.fake_wallet_provider import FakeWalletProvider

    exchange_service = FakeExchangeClient()
    lightning_service = FakeLightningService()
    # WalletProvider multi-tenant (Fase 0). Fake compartido para dev/tests.
    wallet_provider = FakeWalletProvider()
else:
    from infrastructure.exchange.bitso_client import BitsoClient
    from infrastructure.lnbits.lnbits_client import LNbitsClient
    from infrastructure.lnbits.lnbits_wallet_provider import LNbitsWalletProvider

    exchange_service = BitsoClient()
    lightning_service = LNbitsClient()
    wallet_provider = LNbitsWalletProvider(settings.lnbits_url, settings.invoice_expiry)
