from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import Annotated 
from fastapi_limiter.depends import RateLimiter

from sql_app import schemas, crud as db
from sql_app.database import get_db_session
from sql_app.models import User, User_Feedback
from utils import auth

router = APIRouter()

@router.get("/", response_model=schemas.UserBase, dependencies=[Depends(RateLimiter(times=1, seconds=10, identifier=auth.get_identifyer_for_limiter))])
async def get_user(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], session: Session = Depends(get_db_session)):
    user = session.get(User, current_user.id)
    return user

@router.post("/", response_model=schemas.UserBase, dependencies=[Depends(RateLimiter(times=1, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def create_new_user(
    user: schemas.UserCreate,
    session: Session = Depends(get_db_session)
):
    auth.validate_password(user.password)
    db_user = db.get_user_by_email(session, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user.password = auth.get_password_hash(password=user.password)
    return db.create_user(session, user)

@router.patch("/", dependencies=[Depends(RateLimiter(times=1, seconds=30, identifier=auth.get_identifyer_for_limiter))])
def update_user(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], update_items: schemas.UserUpdate,session: Session = Depends(get_db_session)):
    if update_items.password:
        auth.validate_password(update_items.password)
        update_items.password = auth.get_password_hash(update_items.password)
    user = session.get(User, current_user.id)
    update_data = update_items.model_dump(exclude_unset=True)
    
    user.sqlmodel_update(update_data)
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"ok": True}

@router.delete("/", dependencies=[Depends(RateLimiter(times=1, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def delete_user(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],session: Session = Depends(get_db_session)):
    user = session.get(User, current_user.id)

    session.delete(user)
    session.commit()

    return {"ok": True}

@router.post("/feedback", dependencies=[Depends(RateLimiter(times=1, seconds=30, identifier=auth.get_identifyer_for_limiter))])
def create_feedback(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], feedback: schemas.UserFeedback, session: Session = Depends(get_db_session)):
    new_feedback = User_Feedback(
        user_id=current_user.id,
        is_positive=feedback.is_positive,
        title=feedback.title,
        description=feedback.description
    )
    
    session.add(new_feedback)
    session.commit()
    return {'status': True}