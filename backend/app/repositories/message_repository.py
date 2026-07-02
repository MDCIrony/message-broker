import aiosqlite
from typing import List, Dict, Any
from app.models import MessageCreate

class MessageRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create(self, message: MessageCreate) -> Dict[str, Any]:
        """Saves a message to the SQLite database and returns the created record."""
        cursor = await self.db.execute(
            "INSERT INTO messages (topic, payload) VALUES (?, ?) RETURNING id, topic, payload, created_at",
            (message.topic, message.payload)
        )
        row = await cursor.fetchone()
        await self.db.commit()
        return {
            "id": row[0],
            "topic": row[1],
            "payload": row[2],
            "created_at": row[3]
        }

    async def get_by_topic(self, topic: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves messages by topic, sorted by creation time descending."""
        cursor = await self.db.execute(
            "SELECT id, topic, payload, created_at FROM messages WHERE topic = ? ORDER BY id DESC LIMIT ?",
            (topic, limit)
        )
        rows = await cursor.fetchall()
        return [
            {"id": row[0], "topic": row[1], "payload": row[2], "created_at": row[3]}
            for row in rows
        ]

    async def get_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves all messages across all topics, sorted by creation time descending."""
        cursor = await self.db.execute(
            "SELECT id, topic, payload, created_at FROM messages ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [
            {"id": row[0], "topic": row[1], "payload": row[2], "created_at": row[3]}
            for row in rows
        ]

    async def get_unique_topics(self) -> List[str]:
        """Retrieves list of all unique topics in the database."""
        cursor = await self.db.execute("SELECT DISTINCT topic FROM messages ORDER BY topic ASC")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
