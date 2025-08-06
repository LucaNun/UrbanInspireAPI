from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import Annotated 
from fastapi_limiter.depends import RateLimiter
from uuid import uuid4, UUID
from fastapi_mail import MessageSchema, MessageType

from sql_app import schemas, crud as db
from sql_app.database import get_db_session
from sql_app.models import User, User_Feedback, User_Activation
from utils import auth
from utils.mail import fm

router = APIRouter()

@router.get("/", response_model=schemas.UserBase, dependencies=[Depends(RateLimiter(times=1, seconds=10, identifier=auth.get_identifyer_for_limiter))])
async def get_user(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], session: Session = Depends(get_db_session)):
    user = session.get(User, current_user.id)
    return user

@router.post("/", response_model=schemas.UserBase, dependencies=[Depends(RateLimiter(times=1, seconds=60, identifier=auth.get_identifyer_for_limiter))])
async def create_new_user(
    user: schemas.UserCreate,
    session: Session = Depends(get_db_session)
):
    auth.validate_password(user.password)
    db_user = db.get_user_by_email(session, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user.password = auth.get_password_hash(password=user.password)
    
    created_user = db.create_user(session, user)
    uuid = uuid4()
    activation_code = User_Activation(user_id=created_user.id, uuid=uuid)
    session.add(activation_code)
    session.commit()
    try:
        html = f"<p>Jetzt EMail bestätigen!</p><br>https://urban.berellsoft.dev/user/activate/{uuid}"
        
        message = MessageSchema(
            subject="Bestätige deinen Account",
            recipients=[user.email],
            body=html,
            subtype=MessageType.html,
        )
        await fm.send_message(message)
    
    except Exception as e:
        print(f"Fehler beim E-Mail-Versand: {e}")
    
    return created_user

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

    return {"status": True}

@router.delete("/", dependencies=[Depends(RateLimiter(times=1, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def delete_user(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],session: Session = Depends(get_db_session)):
    user = session.get(User, current_user.id)

    session.delete(user)
    session.commit()

    return {"status": True}

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

@router.get("/activate/{id}")
async def simple_send(id: UUID, session: Session = Depends(get_db_session)):
    ua = session.get(User_Activation,id)
    if not ua:
        return {'status': False}
    user = session.get(User, ua.user_id)
    user.is_active = True
    session.delete(ua)
    session.commit()
    return {'status': True}

