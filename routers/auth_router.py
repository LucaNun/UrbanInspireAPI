from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from datetime import datetime, timedelta
from uuid import uuid4
from sqlmodel import Session
import jwt
from jwt.exceptions import InvalidTokenError

from sql_app import crud as db
from sql_app.database import get_db_session
from sql_app import schemas

from utils.auth import authenticate_user, create_access_token, get_current_active_user,oauth2_scheme

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM
from secret import SECRET_KEY


router = APIRouter()


@router.post("/token")
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

@router.post("/logout")
async def logout_and_block_token(current_user: Annotated[schemas.User, Depends(get_current_active_user)], token: Annotated[str, Depends(oauth2_scheme)], session: Session = Depends(get_db_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    ) 
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload = schemas.UserToken(**payload)
        
        blacklist = db.get_user_token_blacklist(session, uuid=payload.uid)
        if not blacklist:
            db.user_token_to_blacklist(session, sub=payload.sub, uuid=payload.uid)


    except InvalidTokenError:
        raise credentials_exception
    
    return True