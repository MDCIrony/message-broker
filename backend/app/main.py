import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import http_router, ws_router

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("broker.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Starting up Message Broker...")
    await init_db()
    yield
    # Shutdown actions
    logger.info("Shutting down Message Broker...")


app = FastAPI(
    title="Custom Message Broker MVP",
    description="A lightweight, topic-agnostic message broker with raw SQL and WebSockets",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(http_router.router)
app.include_router(ws_router.router)
