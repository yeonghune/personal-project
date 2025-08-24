import sentry_sdk
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.services.todo_scheduler import init_scheduler


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize in-memory scheduler
    loop = asyncio.get_running_loop()
    scheduler = init_scheduler(window_minutes=5, hydrate_interval_seconds=60, loop=loop)
    # Hydrate immediately and start background hydrator
    await scheduler.hydrate()
    scheduler.start_background_hydrator()
    yield
    # Shutdown scheduler
    try:
        await scheduler.shutdown()
    except Exception:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
