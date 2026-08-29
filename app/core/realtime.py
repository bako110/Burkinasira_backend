import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Registre en mémoire des connexions WebSocket actives, par user_id.

    Un même utilisateur peut avoir plusieurs connexions actives (plusieurs
    onglets/appareils) : on garde un set de sockets par user_id.
    """

    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    def is_online(self, user_id: str) -> bool:
        return bool(self._connections.get(user_id))

    async def send_to_user(self, user_id: str, event: str, payload: dict) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        message = json.dumps({"event": event, "data": payload}, default=str)
        dead: Set[WebSocket] = set()
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            sockets.discard(ws)
        if not sockets:
            self._connections.pop(user_id, None)


manager = ConnectionManager()
