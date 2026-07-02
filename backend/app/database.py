import aiosqlite
import logging
from app.config import settings

logger = logging.getLogger("broker.database")


async def init_db():
    """Initializes the SQLite database and creates the messages table."""
    logger.info("Initializing database at %s", settings.db_path)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_topic ON messages (topic)
        """)
        await db.commit()
    logger.info("Database initialized successfully.")


async def get_db_connection() -> aiosqlite.Connection:
    """Async generator to yield a database connection for FastAPI dependency injection."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db
