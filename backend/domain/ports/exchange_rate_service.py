from abc import ABC, abstractmethod

from domain.entities.exchange_rate import ExchangeRate


class ExchangeRateService(ABC):
    @abstractmethod
    async def get_rate(self) -> ExchangeRate: ...
