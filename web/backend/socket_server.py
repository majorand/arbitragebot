"""WebSocket server for real-time updates.

Provides a simple connection manager that can be used from FastAPI
routes to accept WebSocket connections and broadcast messages.
"""

from __future__ import annotations

import asyncio
from typing import List

from fastapi import WebSocket


class ConnectionManager:
	def __init__(self) -> None:
		self.active: List[WebSocket] = []

	async def connect(self, websocket: WebSocket) -> None:
		await websocket.accept()
		self.active.append(websocket)

	def disconnect(self, websocket: WebSocket) -> None:
		try:
			self.active.remove(websocket)
		except ValueError:
			pass

	async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
		await websocket.send_text(message)

	async def broadcast(self, message: str) -> None:
		coros = [ws.send_text(message) for ws in list(self.active)]
		if not coros:
			return
		await asyncio.gather(*coros, return_exceptions=True)


manager = ConnectionManager()


__all__ = ["manager", "ConnectionManager"]
