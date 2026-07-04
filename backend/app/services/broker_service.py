import asyncio
import json
import logging
from datetime import datetime
from fastapi import WebSocket
from typing import Dict, Set, Any

logger = logging.getLogger("broker.service")


class BrokerService:
    def __init__(self):
        # Maps topic -> {client_id: WebSocket}
        self.subscriptions: Dict[str, Dict[str, WebSocket]] = {}
        # Maps client_id -> set of topics they subscribed to
        self.client_topics: Dict[str, Set[str]] = {}
        # Live log subscribers (typically dashboard)
        self.log_subscribers: Dict[str, WebSocket] = {}
        # Metadata of active clients
        self.active_clients: Dict[str, Dict[str, Any]] = {}

        # Centralized Logger Initialization (Strategy Pattern)
        from app.services.logger import (
            centralized_logger,
            ConsoleLogStrategy,
            WebSocketLogStrategy,
        )

        centralized_logger.register_strategy(ConsoleLogStrategy())
        centralized_logger.register_strategy(WebSocketLogStrategy(self))

    async def connect_client(
        self, client_id: str, websocket: WebSocket, token: str = None
    ):
        """Registers a new client connection."""
        self.client_topics[client_id] = set()

        # Determine client role based on token
        from app.services.security import security_validator

        role = "unknown"
        if token and token in security_validator._acl:
            role = security_validator._acl[token]["role"]

        client_ip = "unknown"
        if websocket.client:
            client_ip = f"{websocket.client.host}:{websocket.client.port}"

        self.active_clients[client_id] = {
            "client_id": client_id,
            "role": role,
            "ip": client_ip,
            "connected_at": datetime.now().isoformat(),
        }
        await self.log_event("CLIENT_CONNECTED", client_id)

    async def disconnect_client(self, client_id: str):
        """Cleans up all subscriptions and references for a disconnected client."""
        # Unsubscribe from all topics
        if client_id in self.client_topics:
            topics = list(self.client_topics[client_id])
            for topic in topics:
                await self.unsubscribe(client_id, topic)
            del self.client_topics[client_id]

        # Remove from active clients metadata
        self.active_clients.pop(client_id, None)
        # Remove from log subscribers if registered
        self.log_subscribers.pop(client_id, None)
        await self.log_event("CLIENT_DISCONNECTED", client_id)

    async def subscribe(self, client_id: str, topic: str, websocket: WebSocket):
        """Subscribes a client connection to a specific topic."""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = {}
        self.subscriptions[topic][client_id] = websocket
        self.client_topics[client_id].add(topic)
        await self.log_event("CLIENT_SUBSCRIBED", client_id, topic=topic)

    async def unsubscribe(self, client_id: str, topic: str):
        """Unsubscribes a client connection from a specific topic."""
        if topic in self.subscriptions and client_id in self.subscriptions[topic]:
            del self.subscriptions[topic][client_id]
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
        if client_id in self.client_topics and topic in self.client_topics[client_id]:
            self.client_topics[client_id].remove(topic)
        await self.log_event("CLIENT_UNSUBSCRIBED", client_id, topic=topic)

    async def register_log_subscriber(self, client_id: str, websocket: WebSocket):
        """Registers a connection to receive real-time broker logs."""
        self.log_subscribers[client_id] = websocket
        await self.log_event("LOG_SUBSCRIBER_CONNECTED", client_id)

    async def broadcast_to_topic(self, topic: str, message: dict):
        """Sends a message to all active subscribers of a topic."""
        subscribers = self.subscriptions.get(topic, {})
        if not subscribers:
            return

        payload_str = json.dumps(message)
        tasks = []
        for client_id, ws in list(subscribers.items()):
            tasks.append(self._send_safe(client_id, ws, payload_str))

        results = await asyncio.gather(*tasks)
        for failed_id in results:
            if failed_id:
                await self.disconnect_client(failed_id)

        # Calculate accurate count of remaining active subscribers
        active_count = len(self.subscriptions.get(topic, {}))
        await self.log_event(
            "MESSAGE_DISTRIBUTED",
            client_id=f"Broker -> {active_count} clients",
            topic=topic,
            message=message.get("payload"),
        )

    async def log_event(
        self, event_type: str, client_id: str, topic: str = None, message: str = None
    ):
        """Logs a broker event to console and broadcasts it to dashboard subscribers."""
        from app.services.logger import centralized_logger

        await centralized_logger.log_event(event_type, client_id, topic, message)

    async def _send_safe(self, client_id: str, ws: WebSocket, data: str) -> str | None:
        """Safely sends text over WebSocket. Returns client_id if connection failed, else None."""
        try:
            await ws.send_text(data)
            return None
        except Exception:
            logger.warning(
                f"Connection failure for client {client_id}. Scheduling cleanup."
            )
            return client_id


# Single global instance or dependency managed
broker_instance = BrokerService()
