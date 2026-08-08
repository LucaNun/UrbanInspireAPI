from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis

from sql_app.database import insert_data, get_db_session
from routers import auth_router, user_router, idea_router
from config import PRODUCTION, MIN_VERSION, MAINTENANCE_MODE, MAINTENANCE_MESSAGE, MAINTENANCE_RETRY_AFTER, MAINTENANCE_END

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

@app.get("/app/version", tags=["app"])
def get_app_version():
    return {"min_version": MIN_VERSION}

@app.get("/app/maintenance", tags=["app"])
def get_maintenance_status():
    return {
        "maintenance": MAINTENANCE_MODE,
        "message": MAINTENANCE_MESSAGE if MAINTENANCE_MODE else None,
        "retry_after": MAINTENANCE_RETRY_AFTER if MAINTENANCE_MODE else None,
        "estimated_end": MAINTENANCE_END.isoformat() if MAINTENANCE_MODE and MAINTENANCE_END else None,
    }

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(user_router.router, prefix="/user", tags=["user"])
app.include_router(idea_router.router, prefix="/idea", tags=["idea"])
