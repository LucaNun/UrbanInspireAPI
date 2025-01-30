from sqlmodel import Session, select
from . import models, schemas
from datetime import datetime
from uuid import  UUID

def get_user(db: Session, user_id: int):
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

def get_items(db: Session, skip: int = 0, limit: int = 100):
    statement = select(models.Item).offset(skip).limit(limit)
    return db.exec(statement).all()

def store_user_token(db: Session, user_id: int, uuid: UUID, exp: int):
    db_item = models.User_Token(user_id=user_id, uuid=uuid, exp=exp)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_user_token_blacklist(db: Session, uuid: UUID):
    statement = select(models.User_Token_Blacklist).join(models.User_Token, models.User_Token_Blacklist.token_id == models.User_Token.id).where(models.User_Token.uuid == uuid)
    return db.exec(statement).all()

def user_token_to_blacklist(db: Session, uuid: UUID, sub: int):
    item = models.User_Token_Blacklist(token_id=select(models.User_Token.id).where(models.User_Token.uuid == uuid and models.User_Token.user_id == sub))
    db.add(item)
    db.commit()
    db.refresh(item)