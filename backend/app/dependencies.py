import aiosqlite
from fastapi import Depends
from app.database import get_db_connection
from app.repositories.message_repository import MessageRepository
from app.services.broker_service import BrokerService, broker_instance
from app.services.message_service import MessageService


def get_broker_service() -> BrokerService:
    """Dependency provider for the singleton BrokerService."""
    return broker_instance


def get_message_repository(
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> MessageRepository:
    """Dependency provider for the MessageRepository."""
    return MessageRepository(db)


def get_message_service(
    repository: MessageRepository = Depends(get_message_repository),
    broker: BrokerService = Depends(get_broker_service),
) -> MessageService:
    """Dependency provider for the MessageService."""
    return MessageService(repository, broker)
