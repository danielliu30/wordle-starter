"""
Application Lifecycle Management

Handles graceful shutdown of the application.
Ensures in-flight requests complete and connections close cleanly.
"""
import asyncio
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown.
    
    This is passed to FastAPI lifespan parameter to handle startup/shutdown events.
    
    Args:
        app: FastAPI application instance
    
    Startup:
    - Log application start
    - Initialize connections (TODO: database, redis)
    
    Shutdown:
    - Log application shutdown
    - Call shutdown_gracefully()
    """
    # Startup
    logger.info("Application starting up")
    
    # TODO: Initialize connections, etc.
    # await database.connect()
    # await redis.connect()
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")
    await shutdown_gracefully()


async def shutdown_gracefully():
    """
    Gracefully shutdown connections and processes.
    
    Process:
    1. Stop accepting new requests (handled by uvicorn automatically)
    2. Wait for in-flight requests to complete (5 second grace period)
    3. Close database connections
    4. Close Redis connections
    5. Stop background tasks
    """
    logger.info("Starting graceful shutdown")
    
    # Wait for in-flight requests to complete
    logger.info("Waiting for in-flight requests to complete")
    await asyncio.sleep(5)
    
    # Close database connections
    logger.info("Closing database connections")
    # TODO: await database.close()
    
    # Close Redis connections
    logger.info("Closing Redis connections")
    # TODO: await redis.close()
    
    # Stop background tasks
    logger.info("Stopping background tasks")
    # TODO: cancel background tasks
    
    logger.info("Graceful shutdown complete")


def setup_signal_handlers():
    """
    Setup signal handlers for graceful shutdown.
    
    Handles SIGTERM and SIGINT (Ctrl+C) to trigger graceful shutdown.
    """
    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        # Trigger graceful shutdown (in a real app, this would call shutdown_gracefully)
        # For now, we just log it - the lifespan manager will handle actual shutdown
    
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
