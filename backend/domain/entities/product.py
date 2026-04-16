from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Product:
    id: str
    name: str
    price_mxn: float
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
