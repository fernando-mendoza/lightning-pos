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
    # WalletProvider multi-tenant (Fase 0). Fake compartido para dev/tests, con enrutado por
    # credencial: una cadena nostr+walletconnect:// va al provider NWC real también en tests
    # (los tests de ese camino usan relays locales o esperan el 503 honesto).
    from infrastructure.lexe.lexe_wallet_provider import LexeWalletProvider
    from infrastructure.nwc.nwc_wallet_provider import NWCWalletProvider
    from infrastructure.wallet.routing_wallet_provider import RoutingWalletProvider

    wallet_provider = RoutingWalletProvider(
        base=FakeWalletProvider(),
        nwc=NWCWalletProvider(settings.invoice_expiry, allow_insecure_relay=True),
        lexe=LexeWalletProvider(settings.lexe_sidecar_url, settings.invoice_expiry)
        if settings.lexe_sidecar_url
        else None,
    )
else:
    from infrastructure.exchange.bitso_client import BitsoClient
    from infrastructure.lnbits.lnbits_client import LNbitsClient
    from infrastructure.lnbits.lnbits_wallet_provider import LNbitsWalletProvider

    from infrastructure.nwc.nwc_wallet_provider import NWCWalletProvider
    from infrastructure.wallet.routing_wallet_provider import RoutingWalletProvider

    exchange_service = BitsoClient()
    lightning_service = LNbitsClient()
    from infrastructure.lexe.lexe_wallet_provider import LexeWalletProvider

    wallet_provider = RoutingWalletProvider(
        base=LNbitsWalletProvider(settings.lnbits_url, settings.invoice_expiry),
        nwc=NWCWalletProvider(settings.invoice_expiry),
        lexe=LexeWalletProvider(settings.lexe_sidecar_url, settings.invoice_expiry)
        if settings.lexe_sidecar_url
        else None,
    )
