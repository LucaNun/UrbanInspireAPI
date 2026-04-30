from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Annotated
from fastapi_limiter.depends import RateLimiter
from uuid import uuid4, UUID
from fastapi_mail import MessageSchema, MessageType
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from sql_app import schemas, crud as db
from sql_app.database import get_db_session
from sql_app.models import User, User_Feedback, User_Activation, ResetEmailValidation, ResetPassword
from utils import auth
from utils.mail import fm
from config import PASSWORD_RESET_TOKEN_TTL_MINUTES, API_DOMAIN

router = APIRouter()

_TEMPLATES = Path(__file__).parent.parent / "templates"

def _load_template(name: str) -> str:
    return (_TEMPLATES / name).read_text(encoding="utf-8")

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
        try:
            html = _load_template("email_already_registered.html")
            message = MessageSchema(
                subject="Account bereits vorhanden – UrbanInspire",
                recipients=[user.email],
                body=html,
                subtype=MessageType.html,
            )
            await fm.send_message(message)
        except Exception as e:
            print(f"Fehler beim E-Mail-Versand: {e}")
        return schemas.UserBase(
            firstname=db_user.firstname,
            lastname=db_user.lastname,
            username=db_user.username,
            email=db_user.email,
        )
    user.password = auth.get_password_hash(password=user.password)
    
    created_user = db.create_user(session, user)
    uuid = uuid4()
    activation_code = User_Activation(user_id=created_user.id, uuid=uuid)
    session.add(activation_code)
    session.commit()
    try:
        activation_url = f"{API_DOMAIN}/user/activate/{uuid}"
        html = _load_template("activation_email.html").replace("{activation_url}", activation_url)
        message = MessageSchema(
            subject="Bestätige deinen Account – UrbanInspire",
            recipients=[user.email],
            body=html,
            subtype=MessageType.html,
        )
        await fm.send_message(message)
    
    except Exception as e:
        print(f"Fehler beim E-Mail-Versand: {e}")
        return created_user
    
    return created_user

@router.patch("/", dependencies=[Depends(RateLimiter(times=10, seconds=10, identifier=auth.get_identifyer_for_limiter))])
def update_user(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], update_items: schemas.UserUpdate,session: Session = Depends(get_db_session)):
    if update_items.password:
        auth.validate_password(update_items.password)
        update_items.password = auth.get_password_hash(update_items.password)
    user = session.get(User, current_user.id)
    update_data = update_items.model_dump(exclude_unset=True)
    
    user.sqlmodel_update(update_data)
    user.modify_date = datetime.now()
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"status": True}

@router.delete("/", dependencies=[Depends(RateLimiter(times=10, seconds=10, identifier=auth.get_identifyer_for_limiter))])
async def delete_user(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], data: schemas.UserDelete, session: Session = Depends(get_db_session)):
    user = session.get(User, current_user.id)

    if not auth.verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    email = user.email
    session.delete(user)
    session.commit()

    try:
        html = _load_template("account_deleted_email.html")
        message = MessageSchema(
            subject="Account gelöscht – UrbanInspire",
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )
        await fm.send_message(message)
    except Exception as e:
        print(f"Fehler beim E-Mail-Versand: {e}")

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

@router.get("/activate/{id}", response_class=HTMLResponse)
async def activate_account(id: UUID, session: Session = Depends(get_db_session)):
    ua = session.get(User_Activation, id)
    if not ua:
        return HTMLResponse(content=_load_template("activation_error.html"), status_code=404)
    user = session.get(User, ua.user_id)
    user.is_active = True
    session.delete(ua)
    session.commit()
    return HTMLResponse(content=_load_template("activation_success.html"))

@router.post("/reset", dependencies=[Depends(RateLimiter(times=3, seconds=60, identifier=auth.get_identifyer_for_limiter))])
async def reset_Get_Code(data: schemas.UserEmail, session: Session = Depends(get_db_session)):
    user = db.get_user_by_email(session, data.email)
    if not user:
        return {"status": True}
    
    code = f"{secrets.randbelow(1000000):06d}"
    newCode = ResetEmailValidation(
        code=code,
        user_id=user.id,
        ttl=datetime.now() + timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES)
    )
    session.add(newCode)
    session.commit()
    
    try:
        html = _load_template("reset_code_email.html").replace("{reset_code}", code).replace("{ttl_minutes}", str(PASSWORD_RESET_TOKEN_TTL_MINUTES))
        message = MessageSchema(
            subject="Passwort zurücksetzen – UrbanInspire",
            recipients=[user.email],
            body=html,
            subtype=MessageType.html,
        )
        await fm.send_message(message)
    except Exception as e:
        print(f"Fehler beim E-Mail-Versand: {e}")
        raise HTTPException(status_code=500, detail="Error")
    
    return {"status": True}

@router.post("/reset/code", dependencies=[Depends(RateLimiter(times=5, seconds=10, identifier=auth.get_identifyer_for_limiter))])
async def reset_Post_Code(data: schemas.ResetCodeConfirmation, session: Session = Depends(get_db_session)):
    user = db.get_user_by_email(session, data.email)
    if not user:
        raise HTTPException(status_code=401, detail="email and code not matched!")
    statement = select(ResetEmailValidation).select_from(ResetEmailValidation).where(ResetEmailValidation.code==data.code, ResetEmailValidation.user_id == user.id)
    row = session.exec(statement).first()
    
    if not row:
        raise HTTPException(status_code=401, detail="email and code not matched!")
    
    if  row.ttl < datetime.now():
        code = session.get(ResetEmailValidation, row.id)
        session.delete(code)
        session.commit()
        raise HTTPException(status_code=403, detail="token is expired")
        
    code = session.get(ResetEmailValidation, row.id)
    session.delete(code)
    session.commit()
    uuid = uuid4()
    newPasswordRequest = ResetPassword(
        user_id=user.id,
        code=uuid,
        ttl=datetime.now() + timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES)     
    )
    session.add(newPasswordRequest)
    session.commit()
    
    return {"code": uuid}


@router.patch("/reset/password")
async def reset_Password(data: schemas.ResetPassword, session: Session = Depends(get_db_session)):
    statement = select(ResetPassword).select_from(ResetPassword).where(ResetPassword.code == data.code)
    row = session.exec(statement).first()
    if not row:
        raise HTTPException(status_code=401, detail="the uuid does not exist")
    
    if  row.ttl < datetime.now():
        code = session.get(ResetEmailValidation, row.id)
        session.delete(code)
        session.commit()
        raise HTTPException(status_code=403, detail="token is expired")
    
    auth.validate_password(data.password)
    
    session.delete(row)
    session.commit()
    
    hashedPassword = auth.get_password_hash(data.password)
    
    user = session.get(User, row.user_id)
    user.password = hashedPassword
    user.modify_date = datetime.now()
    session.add(user)
    session.commit()
    session.refresh(user)

    try:
        html = _load_template("password_reset_success_email.html")
        message = MessageSchema(
            subject="Passwort erfolgreich geändert – UrbanInspire",
            recipients=[user.email],
            body=html,
            subtype=MessageType.html,
        )
        await fm.send_message(message)
    except Exception as e:
        print(f"Fehler beim E-Mail-Versand: {e}")

    return {"status": True}

