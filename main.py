from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Annotated
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sql_app import schemas
from sql_app import crud as db
from sql_app.database import create_db_and_tables, get_db_session
from sqlmodel import Session
import secret

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto",)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = secret.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(session, username, password):
    user = db.get_user_by_email(session, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM,)
    return encoded_jwt

@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: Session = Depends(get_db_session)
) -> schemas.Token:
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    uuid = uuid4()
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "uid": str(uuid)}, expires_delta=access_token_expires
    )
    exp = datetime.now() + access_token_expires
    db.store_user_token(session, user_id=user.id, uuid=uuid, exp=exp.timestamp())
    return schemas.Token(access_token=access_token, token_type="bearer")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: Session = Depends(get_db_session)) -> schemas.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    ) 
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload = schemas.UserToken(**payload)
        
        blacklist = db.get_user_token_blacklist(session, uuid=payload.uid)
        if blacklist:
            credentials_exception.detail = "Token on Blacklist"
            raise credentials_exception
        if payload.sub is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    result = db.get_user(session, user_id=payload.sub)
    user = schemas.User(**result.model_dump())
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
):  
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user




@app.get("/authItem/")
def is_Auth_Get_Item(current_user: Annotated[schemas.User, Depends(get_current_active_user)]):
    return "Auth + Item"











@app.post("/users/", response_model=schemas.User)
def create_new_user(user: schemas.UserCreate, session: Session = Depends(get_db_session)):
    db_user = db.get_user_by_email(session, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user.password = get_password_hash(password=user.password)
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
