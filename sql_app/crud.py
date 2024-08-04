from sqlmodel import Session, select
from . import models, schemas

def get_user(db: Session, user_id: int):
    return db.get(models.User, user_id)

def get_user_by_email(db: Session, email: str):
    statement = select(models.User).where(models.User.email == email)
    return db.exec(statement).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    statement = select(models.User).offset(skip).limit(limit)
    return db.exec(statement).all()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_items(db: Session, skip: int = 0, limit: int = 100):
    statement = select(models.Item).offset(skip).limit(limit)
    return db.exec(statement).all()

def create_user_item(db: Session, item: schemas.ItemCreate, user_id: int):
    db_item = models.Item(**item.model_dump(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
