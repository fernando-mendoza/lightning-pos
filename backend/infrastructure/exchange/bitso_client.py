import time

import httpx

from config import settings
from domain.entities.exchange_rate import ExchangeRate
from domain.ports.exchange_rate_service import ExchangeRateService


class BitsoClient(ExchangeRateService):
    def __init__(self) -> None:
        self._cache: ExchangeRate | None = None

    async def get_rate(self) -> ExchangeRate:
        now = time.time()
        if self._cache and (now - self._cache.fetched_at) < settings.exchange_rate_ttl:
            return self._cache

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{settings.bitso_api_url}/ticker/?book=btc_mxn"
                )
                resp.raise_for_status()
                data = resp.json()
                last_price = float(data["payload"]["last"])

            self._cache = ExchangeRate(
                mxn_per_btc=last_price,
                fetched_at=now,
                source="bitso",
            )
        except Exception:
            if self._cache:
                return self._cache
            raise

        return self._cache
