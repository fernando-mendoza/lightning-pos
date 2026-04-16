from dataclasses import dataclass


@dataclass
class ExchangeRate:
    mxn_per_btc: float
    fetched_at: float  # unix timestamp
    source: str = "bitso"

    @property
    def sats_per_mxn(self) -> float:
        if self.mxn_per_btc == 0:
            return 0
        return 100_000_000 / self.mxn_per_btc

    def mxn_to_sats(self, amount_mxn: float) -> int:
        return round(amount_mxn * self.sats_per_mxn)
