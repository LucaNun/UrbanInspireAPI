from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from typing import List, Annotated
from sqlmodel import Session

from sql_app import schemas
from sql_app import crud as db
from sql_app.database import create_db_and_tables, get_db_session
from routers import auth_router, user_router, idea_router
from utils import auth

import secret
from config import pwd_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(user_router.router, prefix="/user", tags=["user"])
app.include_router(idea_router.router, prefix="/idea", tags=["idea"])
