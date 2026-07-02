from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from typing import List
from app.models import MessageCreate, MessageResponse
from app.services.message_service import MessageService
from app.dependencies import get_message_service
from app.services.security import security_validator

router = APIRouter(prefix="/api")


def get_token(x_broker_token: str | None = Header(None, alias="X-Broker-Token")) -> str:
    """Dependency to extract and authenticate the X-Broker-Token header."""
    if not x_broker_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header 'X-Broker-Token' is missing",
        )
    if not security_validator.authenticate(x_broker_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Token"
        )
    return x_broker_token


@router.post("/publish", response_model=MessageResponse, status_code=201)
async def publish_message(
    message: MessageCreate,
    token: str = Depends(get_token),
    service: MessageService = Depends(get_message_service),
):
    """Publishes a message to a topic. Requires X-Broker-Token header and publish ACL permissions."""
    if not security_validator.authorize(token, "publish", message.topic):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token is not authorized to publish to topic '{message.topic}'",
        )
    try:
        return await service.publish(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics", response_model=List[str])
async def list_topics(
    token: str = Depends(get_token),
    service: MessageService = Depends(get_message_service),
):
    """Lists all unique topics that have received messages. Requires a valid token."""
    return await service.get_topics()


@router.get("/messages", response_model=List[MessageResponse])
async def list_messages(
    topic: str | None = Query(None, description="Filter messages by topic"),
    limit: int = Query(50, ge=1, le=100, description="Max messages to return"),
    token: str = Depends(get_token),
    service: MessageService = Depends(get_message_service),
):
    """Retrieves message history. Verifies subscribe ACL permissions for the topic."""
    if topic:
        if not security_validator.authorize(token, "subscribe", topic):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token is not authorized to read topic '{topic}'",
            )
        return await service.get_messages_by_topic(topic, limit)
    return await service.get_all_messages(limit)


@router.get("/health")
async def health_check():
    """Simple API health check endpoint."""
    return {"status": "ok", "broker": "custom-mvp"}
