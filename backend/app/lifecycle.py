"""Graceful shutdown handler"""
import asyncio
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up")
    yield
    logger.info("Application shutting down")
    await shutdown_gracefully()

async def shutdown_gracefully():
    logger.info("Starting graceful shutdown")
    await asyncio.sleep(5)
    logger.info("Graceful shutdown complete")

def setup_signal_handlers():
    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}")
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
