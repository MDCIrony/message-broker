import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.models import MessageCreate
from app.services.broker_service import BrokerService
from app.services.message_service import MessageService
from app.dependencies import get_broker_service, get_message_service
from app.services.security import security_validator

router = APIRouter()
logger = logging.getLogger("broker.ws")


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    token: str | None = None,
    broker: BrokerService = Depends(get_broker_service),
    message_service: MessageService = Depends(get_message_service),
):
    """WebSocket connection handler. Authenticates token and authorizes actions via ACLs."""
    await websocket.accept()

    # 1. Authenticate token
    if not token or not security_validator.authenticate(token):
        await websocket.send_json({"error": "Unauthorized: Invalid or missing token"})
        await websocket.close(code=4003)
        return

    await broker.connect_client(client_id, websocket, token)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                action = data.get("action")

                if action == "subscribe":
                    topic = data.get("topic")
                    if topic:
                        if security_validator.authorize(token, "subscribe", topic):
                            await broker.subscribe(client_id, topic, websocket)
                            await websocket.send_json({"event": "subscribed", "topic": topic})
                        else:
                            await websocket.send_json({
                                "error": f"Forbidden: No subscribe ACL for '{topic}'",
                                "action": "subscribe",
                                "topic": topic
                            })

                elif action == "unsubscribe":
                    topic = data.get("topic")
                    if topic:
                        await broker.unsubscribe(client_id, topic)
                        await websocket.send_json({"event": "unsubscribed", "topic": topic})

                elif action == "publish":
                    topic = data.get("topic")
                    payload = data.get("payload")
                    if topic and payload is not None:
                        if security_validator.authorize(token, "publish", topic):
                            await message_service.publish(
                                MessageCreate(topic=topic, payload=payload)
                            )
                        else:
                            await websocket.send_json(
                                {"error": f"Forbidden: No publish ACL for '{topic}'"}
                            )

                elif action == "register_logs":
                    # Restrict server events logs to the admin credentials only
                    if token == "admin-token-999":
                        await broker.register_log_subscriber(client_id, websocket)
                    else:
                        await websocket.send_json(
                            {"error": "Forbidden: Admin token required for logs"}
                        )

                else:
                    await websocket.send_json({"error": f"Unknown action: {action}"})

            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
            except Exception as e:
                logger.error("Error processing WS message: %s", str(e))
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        pass
    finally:
        await broker.disconnect_client(client_id)
