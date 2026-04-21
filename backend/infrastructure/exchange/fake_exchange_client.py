import time

from domain.entities.exchange_rate import ExchangeRate
from domain.ports.exchange_rate_service import ExchangeRateService


class FakeExchangeClient(ExchangeRateService):
    """Rate fijo para tests. 1 BTC = 2,000,000 MXN.
    Se activa cuando LPOS_TEST_MODE=1."""

    FIXED_RATE_MXN_PER_BTC = 2_000_000.0

    async def get_rate(self) -> ExchangeRate:
        return ExchangeRate(
            mxn_per_btc=self.FIXED_RATE_MXN_PER_BTC,
            fetched_at=time.time(),
            source="fake",
        )
