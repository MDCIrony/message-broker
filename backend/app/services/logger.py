import logging
import json
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger("broker.central")


class BaseLogStrategy(ABC):
    @abstractmethod
    async def log(self, event: dict):
        """Performs the logging operation for the given event."""
        pass


class ConsoleLogStrategy(BaseLogStrategy):
    async def log(self, event: dict):
        """Logs event to the standard Python console logger."""
        logger.info(
            f"[{event['event_type']}] Client: {event['client_id']} | "
            f"Topic: {event.get('topic')} | Msg: {event.get('message')}"
        )


class WebSocketLogStrategy(BaseLogStrategy):
    def __init__(self, broker):
        # We pass the broker instance to avoid circular imports
        self.broker = broker

    async def log(self, event: dict):
        """Broadcasts logging events to all active dashboard connections."""
        if self.broker.log_subscribers:
            event_str = json.dumps(event)
            # Safe send over WebSocket to all registered logs subscribers
            import asyncio

            tasks = [
                self.broker._send_safe(cid, ws, event_str)
                for cid, ws in list(self.broker.log_subscribers.items())
            ]
            results = await asyncio.gather(*tasks)
            for failed_id in results:
                if failed_id:
                    await self.broker.disconnect_client(failed_id)


class CentralizedLogger:
    def __init__(self):
        self._strategies = []

    def register_strategy(self, strategy: BaseLogStrategy):
        self._strategies.append(strategy)

    async def log_event(
        self, event_type: str, client_id: str, topic: str = None, message: str = None
    ):
        """Constructs an event and distributes it across all registered logging strategies."""
        event = {
            "event_type": event_type,
            "client_id": client_id,
            "topic": topic,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        for strategy in self._strategies:
            try:
                await strategy.log(event)
            except Exception as e:
                # Prevent logging errors from crashing the main broker thread
                logger.error(
                    f"Error in logging strategy {strategy.__class__.__name__}: {str(e)}"
                )


# Global instance initialized during startup
centralized_logger = CentralizedLogger()
