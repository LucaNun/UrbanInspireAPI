from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis

from sql_app.database import insert_data, get_db_session
from routers import auth_router, user_router, idea_router

import secret


@asynccontextmanager
async def lifespan(app: FastAPI):
    insert_data()
    redis_c = redis.from_url(f"redis://{secret.REDIS_IP}", encoding="utf8", decode_responses=True)
    await FastAPILimiter.init(redis_c)
    yield
    await redis_c.close()

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(user_router.router, prefix="/user", tags=["user"])
app.include_router(idea_router.router, prefix="/idea", tags=["idea"])
