from typing import List, Dict, Any
from app.repositories.message_repository import MessageRepository
from app.services.broker_service import BrokerService
from app.models import MessageCreate


class MessageService:
    def __init__(self, repository: MessageRepository, broker: BrokerService):
        self.repository = repository
        self.broker = broker

    async def publish(self, message: MessageCreate) -> Dict[str, Any]:
        """Persists a message in DB, logs it, and broadcasts it to topic subscribers."""
        # 1. Save to DB
        saved_msg = await self.repository.create(message)

        # 2. Log message arrival at broker
        await self.broker.log_event(
            event_type="MESSAGE_RECEIVED",
            client_id="Producer",
            topic=message.topic,
            message=message.payload,
        )

        # 3. Broadcast to all active subscribers
        await self.broker.broadcast_to_topic(message.topic, saved_msg)

        return saved_msg

    async def get_messages_by_topic(
        self, topic: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieves history for a topic."""
        return await self.repository.get_by_topic(topic, limit)

    async def get_all_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves all message history."""
        return await self.repository.get_all(limit)

    async def get_topics(self) -> List[str]:
        """Retrieves list of active topics from DB."""
        return await self.repository.get_unique_topics()
