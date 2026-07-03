from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from typing import List
from app.models import MessageCreate, MessageResponse
from app.services.message_service import MessageService
from app.services.broker_service import BrokerService
from app.dependencies import get_message_service, get_broker_service
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
    # Ensure the token has subscribe permissions in general
    acl_rules = security_validator._acl.get(token)
    if not acl_rules or "subscribe" not in acl_rules.get("allowed_actions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is not authorized to read messages",
        )

    if topic:
        if not security_validator.authorize(token, "subscribe", topic):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token is not authorized to read topic '{topic}'",
            )
        return await service.get_messages_by_topic(topic, limit)
    
    # Check if the token is authorized to subscribe/read each message's topic
    all_messages = await service.get_all_messages(limit)
    return [
        msg for msg in all_messages
        if security_validator.authorize(token, "subscribe", msg["topic"])
    ]




@router.get("/admin/status")
async def get_admin_status(
    token: str = Depends(get_token),
    broker: BrokerService = Depends(get_broker_service),
    service: MessageService = Depends(get_message_service),
):
    """Returns detailed real-time broker status. Admin token required."""
    if token != "admin-token-999":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin credentials required for status"
        )
    
    clients_info = []
    for client_id, meta in broker.active_clients.items():
        subscribed_topics = list(broker.client_topics.get(client_id, []))
        is_log_sub = client_id in broker.log_subscribers
        clients_info.append({
            "client_id": client_id,
            "role": meta["role"],
            "ip": meta["ip"],
            "connected_at": meta["connected_at"],
            "subscriptions": subscribed_topics,
            "is_log_subscriber": is_log_sub
        })
        
    unique_topics = await service.get_topics()
    
    return {
        "active_clients_count": len(broker.active_clients),
        "active_clients": clients_info,
        "topics": unique_topics,
        "subscriptions_raw": {topic: list(subs.keys()) for topic, subs in broker.subscriptions.items()}
    }


@router.get("/health")
async def health_check():
    """Simple API health check endpoint."""
    return {"status": "ok", "broker": "custom-mvp"}
