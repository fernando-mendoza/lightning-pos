import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)

    async def broadcast_payment(self, payment_hash: str, sale_id: str) -> None:
        message = json.dumps({
            "type": "payment_confirmed",
            "payment_hash": payment_hash,
            "sale_id": sale_id,
        })
        stale = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self._connections.remove(ws)


ws_manager = ConnectionManager()
