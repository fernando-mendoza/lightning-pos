from domain.entities.exchange_rate import ExchangeRate
from domain.ports.exchange_rate_service import ExchangeRateService


async def get_exchange_rate(service: ExchangeRateService) -> ExchangeRate:
    return await service.get_rate()
