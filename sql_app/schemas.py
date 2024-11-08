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
    firstname: str
    lastname: str
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
  
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