"""
LLM Router - FastAPI application entry point.

A smart API gateway for routing LLM requests to multiple providers.
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import settings
from src.utils.logging import setup_logging, logger
from src.db.base import init_db, close_db
from src.config.redis_config import RedisConfig
from src.agents.gateway_orchestrator import orchestrator
from src.agents.routing_agent import routing_agent
from src.agents.provider_agent import provider_agent
from src.api.middleware import setup_cors, LoggingMiddleware
from src.api.v1 import chat, router, cost, providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting LLM Router...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Initialize Redis
    try:
        redis_client = await RedisConfig.get_client()
        await redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    # Initialize orchestrator
    try:
        await orchestrator.initialize()
        logger.info("Gateway Orchestrator initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Gateway Orchestrator: {e}")

    # Initialize routing agent
    try:
        await routing_agent.initialize()
        logger.info("Routing Agent initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Routing Agent: {e}")

    # Initialize provider agent
    try:
        await provider_agent.initialize()
        logger.info("Provider Agent initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Provider Agent: {e}")

    logger.info("LLM Router started successfully")

    yield

    # Shutdown
    logger.info("Shutting down LLM Router...")
    await close_db()
    await RedisConfig.close()
    logger.info("LLM Router shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Intelligent multi-model API gateway for LLMs",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Setup CORS
setup_cors(app)

# Add logging middleware
app.add_middleware(LoggingMiddleware)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "detail": str(exc) if settings.debug else None,
            }
        },
    )


# Middleware for request timing
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add timing information to response."""
    start_time = time.time()
    request.state.start = start_time
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    return response


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis
        redis_client = await RedisConfig.get_client()
        redis_healthy = await redis_client.ping()

        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "redis": "connected" if redis_healthy else "disconnected",
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
            },
        )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with basic information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Intelligent multi-model API gateway for LLMs",
        "docs": "/docs" if settings.debug else None,
        "health": "/health",
    }


# Include API routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(router.router, prefix="/api/v1")
app.include_router(cost.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
