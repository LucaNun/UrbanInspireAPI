import jwt
from jwt.exceptions import InvalidTokenError
from datetime import timezone, timedelta, datetime
from typing import Annotated
from sqlmodel import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sql_app import schemas
from sql_app.database import get_db_session
from sql_app import crud as db

from config import pwd_context, ALGORITHM
from secret import SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def validate_password(value):
        if not any(char.isdigit() for char in value):
            raise HTTPException(status_code=400, detail="Password must contain at least one digit.")
        if not any(char.isupper() for char in value):
            raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in value):
            raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter.")
        if not any(char in "!@#$%^&*()_+-=[]{}|;':,.<>?/~`" for char in value):
            raise HTTPException(status_code=400, detail="Password must contain at least one special character.")
        if not len(value) > 8:
            raise HTTPException(status_code=400, detail="Password must contain more than 8 characters.")
        return value

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
    if not result:
        raise credentials_exception
    user = schemas.User(**result.model_dump())
    return user


async def get_current_active_user(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
):  
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user