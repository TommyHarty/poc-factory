"""POC Factory FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    settings = get_settings()
    logger = get_logger(__name__)

    # Initialize database
    try:
        from app.infrastructure.persistence.database import init_db
        db_path = str(settings.work_root / "poc_factory.db")
        Path(settings.work_root).mkdir(parents=True, exist_ok=True)
        Path(settings.output_root).mkdir(parents=True, exist_ok=True)
        await init_db(db_path)
        logger.info("database_initialized", path=db_path)
    except Exception as e:
        logger.error("database_init_failed", error=str(e))

    logger.info(
        "app_started",
        name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )

    yield

    logger.info("app_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="POC Factory",
        description="Agentic POC generation platform for agentic systems topics",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS (for future frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from app.api.routes.health import router as health_router
    from app.api.routes.runs import router as runs_router

    app.include_router(health_router)
    app.include_router(runs_router)

    return app


app = create_app()
