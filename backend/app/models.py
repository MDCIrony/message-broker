from pydantic import BaseModel
from datetime import datetime


class MessageCreate(BaseModel):
    topic: str
    payload: str


class MessageResponse(BaseModel):
    id: int
    topic: str
    payload: str
    created_at: str


class SystemEvent(BaseModel):
    event_type: str  # CONNECT, DISCONNECT, MESSAGE_RECEIVED, MESSAGE_DISTRIBUTED
    client_id: str
    topic: str | None = None
    message: str | None = None
    timestamp: str
