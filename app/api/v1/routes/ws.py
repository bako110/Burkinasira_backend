from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from app.core.realtime import manager
from app.core.security import decode_token

router = APIRouter(tags=["Temps réel"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """Canal temps réel unique par utilisateur (messagerie + notifications).

    Authentification par JWT passé en query param (`?token=...`), seule
    option praticable pour un WebSocket natif sans en-têtes personnalisés.
    Émet des évènements `{"event": "...", "data": {...}}` :
    - "message.new" : nouveau message de chat reçu
    - "notification.new" : nouvelle notification reçue
    - "booking.updated" : changement de statut d'une réservation liée
    """
    try:
        current_user = decode_token(token)
    except (JWTError, Exception):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = current_user.sub
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Le client n'a rien à envoyer sur ce canal ; on lit uniquement
            # pour détecter la déconnexion (ping/pong gérés par le framework).
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
