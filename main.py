from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis

from sql_app.database import insert_data, get_db_session
from routers import auth_router, user_router, idea_router
from config import PRODUCTION, MIN_VERSION, MAINTENANCE_MODE, MAINTENANCE_CODE, MAINTENANCE_MESSAGE, MAINTENANCE_RETRY_AFTER, MAINTENANCE_START, MAINTENANCE_END

import secret


@asynccontextmanager
async def lifespan(app: FastAPI):
    insert_data()
    redis_c = redis.from_url(f"redis://{secret.REDIS_IP}", encoding="utf8", decode_responses=True)
    await FastAPILimiter.init(redis_c)
    yield
    await redis_c.close()

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

@app.get("/app/version", tags=["app"])
def get_app_version():
    return {"min_version": MIN_VERSION}

@app.get("/app/maintenance", tags=["app"])
def get_maintenance_status():
    return {
        "maintenance": MAINTENANCE_MODE,
        "code": MAINTENANCE_CODE if MAINTENANCE_MODE else None,
        "message": MAINTENANCE_MESSAGE if MAINTENANCE_MODE else None,
        "retry_after": MAINTENANCE_RETRY_AFTER if MAINTENANCE_MODE else None,
        "min_version": MIN_VERSION if MAINTENANCE_MODE else None,
        "estimated_start": MAINTENANCE_START.isoformat() if MAINTENANCE_START and MAINTENANCE_MODE else None,
        "estimated_end": MAINTENANCE_END.isoformat() if MAINTENANCE_END and MAINTENANCE_MODE else None,
    }

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(user_router.router, prefix="/user", tags=["user"])
app.include_router(idea_router.router, prefix="/idea", tags=["idea"])
