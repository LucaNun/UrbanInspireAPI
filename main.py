from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from typing import List, Annotated
from sqlmodel import Session

from sql_app import schemas
from sql_app import crud as db
from sql_app.database import create_db_and_tables, get_db_session
from routers import auth_router
from utils import auth

import secret
from config import pwd_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])




@app.get("/authItem/")
def is_Auth_Get_Item(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)]):
    return "Auth + Item"




@app.post("/users/", response_model=schemas.User)
def create_new_user(user: schemas.UserCreate, session: Session = Depends(get_db_session)):
    auth.validate_password(user.password)
    db_user = db.get_user_by_email(session, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user.password = auth.get_password_hash(password=user.password)
    return db.create_user(session, user)

@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 10, session: Session = Depends(get_db_session)):
    users = db.get_users(session, skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, session: Session = Depends(get_db_session)):
    db_user = db.get_user(session, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/users/{user_id}/items/", response_model=schemas.Item)
def create_item_for_user(user_id: int, item: schemas.ItemCreate, session: Session = Depends(get_db_session)):
    return db.create_user_item(session, item, user_id)

@app.get("/items/", response_model=List[schemas.Item])
def read_items(skip: int = 0, limit: int = 10, session: Session = Depends(get_db_session)):
    items = db.get_items(session, skip=skip, limit=limit)
    return items



