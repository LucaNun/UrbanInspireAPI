from sqlmodel import Session, select, and_
from . import models, schemas
from datetime import datetime
from uuid import UUID

def get_user(db: Session, user_id: UUID):
    return db.get(models.User, user_id)

def get_user_by_email(db: Session, email: str):
    statement = select(models.User).where(models.User.email == email)
    return db.exec(statement).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    statement = select(models.User).offset(skip).limit(limit)
    return db.exec(statement).all()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(email=user.email, password=user.password, firstname=user.firstname, lastname=user.lastname, username=user.username, creation_date=datetime.now(), modify_date=datetime.now())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def store_user_token(db: Session, user_id: UUID, uuid: UUID, exp: int):
    db_item = models.User_Token(user_id=user_id, uuid=uuid, exp=exp)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def is_token_blacklisted(db: Session, uuid: UUID) -> bool:
    token = db.exec(select(models.User_Token).where(models.User_Token.uuid == uuid)).first()
    return token is not None and token.is_blacklisted

def user_token_to_blacklist(db: Session, uuid: UUID, sub: UUID):
    token = db.exec(
        select(models.User_Token).where(
            and_(models.User_Token.uuid == uuid, models.User_Token.user_id == sub)
        )
    ).first()
    if not token:
        return
    token.is_blacklisted = True
    db.add(token)
    db.commit()
