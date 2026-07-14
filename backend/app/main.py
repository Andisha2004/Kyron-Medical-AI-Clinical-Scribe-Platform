from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database_session
from app.api import auth, encounters, icd, notes, patients, providers, templates, voice
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.schemas.health import HealthResponse

settings = get_settings()
configure_logging(settings)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting application", extra={"environment": settings.app_env})
    yield
    logger.info("Shutting down application", extra={"environment": settings.app_env})


api_router = APIRouter(prefix="/api")


async def _health_response(session: AsyncSession | None = None) -> HealthResponse:
    database_status = None
    if session is not None:
        try:
            await session.execute(text("SELECT 1"))
            database_status = "ok"
        except Exception:
            database_status = "error"

    return HealthResponse(
        service=settings.app_name,
        environment=settings.app_env,
        database_status=database_status,
        database_pool={
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_recycle_seconds": settings.database_pool_recycle_seconds,
            "pool_pre_ping": settings.database_pool_pre_ping,
        },
    )


@api_router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(
    session: AsyncSession = Depends(get_database_session),
) -> HealthResponse:
    return await _health_response(session)


api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(encounters.router)
api_router.include_router(notes.router)
api_router.include_router(templates.router)
api_router.include_router(providers.router)
api_router.include_router(icd.router)
api_router.include_router(voice.router)

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)
app.add_api_route("/health", health_check, methods=["GET"], response_model=HealthResponse, tags=["health"])
