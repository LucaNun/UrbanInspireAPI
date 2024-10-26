from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    owner_id: int

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    firstname: str
    lastname: str
    username: str
    password: str

class User(UserBase):
    id: int
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class UserToken(BaseModel):
    sub: int
    uid: UUID
    exp: int