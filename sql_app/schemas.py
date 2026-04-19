from pydantic import BaseModel, EmailStr, FilePath, Field
from typing import Optional, List, Annotated
from uuid import UUID
from datetime import datetime
import re

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

class UserFeedback(BaseModel):
    title: str
    description: str
    is_positive: bool

class IdeaBase(BaseModel):
    id: int
    title: str
    description: Optional[str]
    latitude: float
    longitude: float
    nearest_city: str
    location_radius: float
    status_id: int
    category_id: int
    owner_id: int
    modify_date: datetime
    creation_date: datetime
    images: List["IdeaImage"]

class GetCreateIdea(BaseModel):
    title: str
    latitude: float
    longitude: float
    nearest_city: str
    location_radius: float
    status: int
    description: str
    category: int

class Idea_Create(GetCreateIdea):
    owner_id: int

class IdeaImage(BaseModel):
    id: int
    user_id: int
    image_path: str
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
    
class IdeaCategory(BaseModel):
    id: int
    name: str

class IdeaCategoryWithUsage(IdeaCategory):
    usage: float

class IdeasStatus(BaseModel):
    id: int
    name: str


class IdeaNearbyItem(IdeaBase):
    distance_km: float    

# Password Reset
class UserEmail(BaseModel):
    email: EmailStr
class ResetCodeConfirmation(UserEmail):
    code: Annotated[str, Field(pattern=r'^\d{6}$')]
class ResetCode(BaseModel):
    code: UUID
class ResetPassword(ResetCode):
    password: str