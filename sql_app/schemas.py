from pydantic import BaseModel, EmailStr, FilePath
from typing import Optional, List
from uuid import UUID

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
    
    
class Idea(BaseModel):
    title: str
    latitude: float
    longitude: float
    nearest_city: str
    location_radius: float
    status: int
    description: str

class Idea_Create(Idea):
    owner_id: int

class IdeaImage(BaseModel):
    idea_id: int
    user_id: int
    image_path: FilePath
    name: str
    
class IdeaImageCreate(BaseModel):
    name: str

class IdeaUpdate(BaseModel):
    id: int
    title: Optional[str] = None
    latitude: Optional[float] = None 
    longitude: Optional[float] = None 
    nearest_city: Optional[str] = None
    location_radius: Optional[float] = None
    status: Optional[int] = None 
    description: Optional[str] = None