from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from utils.rate_limiter import rate_limited
from utils.redis_client import redis_client

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from sql_app.database import insert_data, get_db_session, cleanup_tokens, cleanup_unactiveded_users, cleanup_unused_password_reset_tokens
from routers import auth_router, user_router, idea_router
from config import PRODUCTION, MIN_VERSION, MAINTENANCE_MODE, MAINTENANCE_CODE, MAINTENANCE_MESSAGE, MAINTENANCE_RETRY_AFTER, MAINTENANCE_START, MAINTENANCE_END

scheduler = AsyncIOScheduler()
@asynccontextmanager
async def lifespan(app: FastAPI):
    insert_data()
    
    scheduler.add_job(
        cleanup_tokens,
        "interval",
        minutes=15,
        id="cleanup_sessions",
        replace_existing=True,
    )
    
    scheduler.add_job(
        cleanup_unactiveded_users,
        "interval",
        days=1,
        id="cleanup_unactive_users",
        replace_existing=True,
    )
    
    scheduler.add_job(
        cleanup_unused_password_reset_tokens,
        "interval",
        days=1,
        id="cleanup_unused_password_reset_tokens",
        replace_existing=True,
    )
    
    scheduler.start()
    yield
    print("Shutting down...")
    scheduler.shutdown()
    await redis_client.aclose()
    print("Shutting down complete.")

app = FastAPI(
    lifespan=lifespan,
    docs_url=None if PRODUCTION else "/docs",
    redoc_url=None if PRODUCTION else "/redoc",
    openapi_url=None if PRODUCTION else "/openapi.json"    
)

@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    if MAINTENANCE_MODE and request.url.path != "/app/maintenance":
        headers = {"Retry-After": str(MAINTENANCE_RETRY_AFTER)} if MAINTENANCE_RETRY_AFTER else {}
        return JSONResponse(
            status_code=503,
            headers=headers,
            content={
                "maintenance": MAINTENANCE_MODE,
                "code": MAINTENANCE_CODE,
                "message": MAINTENANCE_MESSAGE,
                "retry_after": MAINTENANCE_RETRY_AFTER,
                "min_version": MIN_VERSION,
                "estimated_start": MAINTENANCE_START.isoformat() if MAINTENANCE_START else None,
                "estimated_end": MAINTENANCE_END.isoformat() if MAINTENANCE_END else None,
            },
        )
    return await call_next(request)

@app.get("/app/version", dependencies=rate_limited("app:version", 10, 20), tags=["app"])
def get_app_version():
    return {"min_version": MIN_VERSION}

@app.get("/app/maintenance", dependencies=rate_limited("app:maintenance", 10, 20), tags=["app"])
def get_maintenance_status():
    headers = {"Retry-After": str(MAINTENANCE_RETRY_AFTER)} if MAINTENANCE_RETRY_AFTER else {}
    return JSONResponse(
        status_code=503 if MAINTENANCE_MODE else 200,
        headers=headers,
        content={
            "maintenance": MAINTENANCE_MODE,
            "code": MAINTENANCE_CODE if MAINTENANCE_MODE else None,
            "message": MAINTENANCE_MESSAGE if MAINTENANCE_MODE else None,
            "retry_after": MAINTENANCE_RETRY_AFTER if MAINTENANCE_MODE else None,
            "min_version": MIN_VERSION if MAINTENANCE_MODE else None,
            "estimated_start": MAINTENANCE_START.isoformat() if MAINTENANCE_START and MAINTENANCE_MODE else None,
            "estimated_end": MAINTENANCE_END.isoformat() if MAINTENANCE_END and MAINTENANCE_MODE else None,
        }
    )

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(user_router.router, prefix="/user", tags=["user"])
app.include_router(idea_router.router, prefix="/idea", tags=["idea"])
