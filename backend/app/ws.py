from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect


class WebSocketManager:
    """
    Very lightweight WebSocket connection manager.

    Single-session app for now, but structured to allow
    multiple connections / sessions later.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast JSON-serializable message to all clients.
        """
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)


# Global manager
WS_MANAGER = WebSocketManager()
