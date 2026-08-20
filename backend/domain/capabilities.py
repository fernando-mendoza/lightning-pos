"""Regla pura: qué puede cobrar un tenant.

Vive en el dominio y sin dependencias (ni ORM ni settings) por dos razones: es una regla de
negocio, y así se puede testear en aislamiento — el contenedor de tests sólo copia módulos
puros, y una regla que exige levantar Postgres para verificarse termina sin verificarse.
"""

from __future__ import annotations

CASH = "cash"
LIGHTNING = "lightning"


def wallet_is_usable(
    provider: str | None, wallet_id: str | None, invoice_key_enc: str | None
) -> bool:
    """¿Esta wallet puede emitir un cobro, o es un alta a medias?

    Sin credencial no hay nada que hacer. Y en LNbits, un `wallet_id` ausente es exactamente
    un alta a medias: el tenant quedó registrado, con llave guardada, creyendo que podía
    cobrar. Le pasó a AgentykCo y no se detectó hasta el censo, semanas después.
    """
    if not invoice_key_enc:
        return False
    if provider == "lnbits":
        return bool(wallet_id)
    return True
