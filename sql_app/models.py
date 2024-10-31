from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr, field_validator, FilePath
from typing import Optional, List
from uuid import UUID
from datetime import timedelta


class User_Feedback(SQLModel, table=True):
    __tablename__ = "User_Feedback"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="Users.id")
    feedback_value: bool
    title: str
    text: str
    
    user: "User" = Relationship(back_populates="feedback")

  
class Idea(SQLModel, table=True):
    __tablename__ = "Ideas"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    title_image: Optional[int] = Field(default=None, foreign_key="Idea_Images.id")
    latitude: float
    longitude: float
    nearest_city: str
    location_radius: float
    status: Optional[int] = Field(default=None, foreign_key="Idea_Status.id")
    description: Optional[str] = None
    owner_id: Optional[int] = Field(default=None, foreign_key="Users.id")

    owner: "User" = Relationship(back_populates="ideas")
    #title_img: "Idea_Image" = Relationship(back_populates="idea")
    
    @field_validator("latitude")
    def validate_latitude(cls, value):
        if not (-90 <= value <= 90):
            raise ValueError("Latitude must be between -90 and 90.")
        return value

    @field_validator("longitude")
    def validate_longitude(cls, value):
        if not (-180 <= value <= 180):
            raise ValueError("Longitude must be between -180 and 180.")
        return value

class Idea_Status(SQLModel, table=True):
    __tablename__ = "Idea_Status"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    #ideas: "Idea" = Relationship(back_populates="status")

class Idea_Image(SQLModel, table=True):
    __tablename__ = "Idea_Images"
    id: Optional[int] = Field(default=None, primary_key=True)
    idea_id: Optional[int] = Field(default=None,foreign_key="Ideas.id", ondelete="CASCADE")
    image_path: FilePath
    name: str
    
    #idea: "Idea" = Relationship(back_populates="images")


class User_Token(SQLModel, table=True):
    __tablename__ = "User_Token"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None,foreign_key="Users.id", ondelete="CASCADE")
    uuid: UUID
    exp: int
    
    user: "User" = Relationship(back_populates="tokens")
    blacklist: "User_Token_Blacklist" = Relationship(back_populates="token")
    
class User_Token_Blacklist(SQLModel, table=True):
    __tablename__ = "User_Token_Blacklist"
    id: Optional[int] = Field(default=None, primary_key=True)
    token_id: int = Field(foreign_key="User_Token.id", ondelete="CASCADE")
    
    token: User_Token = Relationship(back_populates="blacklist")
    
class User(SQLModel, table=True):
    __tablename__ = "Users"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_group: int = Field(default=2, foreign_key="User_Groups.id", ondelete="CASCADE")
    firstname: str
    lastname: str
    username: str
    email: EmailStr
    password: str
    is_active: bool = Field(default=True)

    ideas: List[Idea] = Relationship(back_populates="owner")
    tokens: List[User_Token] = Relationship(back_populates="user")
    feedback: List["User_Feedback"] = Relationship(back_populates="user")

class User_Group(SQLModel, table=True):
    __tablename__ = "User_Groups"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
