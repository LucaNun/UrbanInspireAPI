from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr, field_validator, GetCoreSchemaHandler
from pydantic_core import core_schema
from typing import Optional, List, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import Column
from geoalchemy2 import Geography


class _Geography:
    """Wrapper so pydantic-core always serializes the PostGIS column as None."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler):
        return core_schema.no_info_plain_validator_function(
            lambda v: v,
            serialization=core_schema.plain_serializer_function_ser_schema(lambda v: None),
        )


class User_Feedback(SQLModel, table=True):
    __tablename__ = "User_Feedback"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="Users.id", ondelete="SET NULL", nullable=True)
    is_positive: bool
    title: str
    description: str

    user: "User" = Relationship(back_populates="feedback")

class Image_To_Idea(SQLModel, table=True):
    __tablename__ = "Image_To_Idea"
    idea_id: Optional[UUID] = Field(default=None, foreign_key="Ideas.id", ondelete="CASCADE", primary_key=True)
    image_id: Optional[UUID] = Field(default=None, foreign_key="Idea_Images.id", ondelete="CASCADE", primary_key=True)

class Idea(SQLModel, table=True):
    __tablename__ = "Ideas"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    latitude: float
    longitude: float
    nearest_city: str
    location_radius: float
    status_id: Optional[int] = Field(default=1, foreign_key="Idea_Status.id", ondelete="SET NULL", nullable=True, index=True)
    description: Optional[str] = None
    owner_id: Optional[UUID] = Field(default=None, foreign_key="Users.id", ondelete="SET NULL", nullable=True, index=True)
    creation_date: datetime
    modify_date: datetime
    category_id: Optional[int] = Field(default=1, foreign_key="Idea_Categories.id", ondelete="SET NULL", nullable=True, index=True)
    location: Optional[_Geography] = Field(
        default=None,
        sa_column=Column(Geography(geometry_type='POINT', srid=4326), nullable=True),
    )

    owner: "User" = Relationship(back_populates="ideas")

    images: list["Idea_Image"] = Relationship(
        back_populates="idea",
        link_model=Image_To_Idea
    )

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
    public: bool = Field(default=False)

class Idea_Image(SQLModel, table=True):
    __tablename__ = "Idea_Images"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="Users.id", ondelete="SET NULL", nullable=True)
    name: str

    idea: list[Idea] = Relationship(
        back_populates="images",
        link_model=Image_To_Idea
    )

class Idea_Likes(SQLModel, table=True):
    __tablename__ = "Idea_Likes"
    idea_id: UUID = Field(foreign_key="Ideas.id", primary_key=True, ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="Users.id", primary_key=True, ondelete="CASCADE")
    like: bool

class Idea_Categories(SQLModel, table=True):
    __tablename__ = "Idea_Categories"
    id: int = Field(default=None, primary_key=True)
    name: str

class User_Token(SQLModel, table=True):
    __tablename__ = "User_Token"
    uuid: UUID = Field(primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="Users.id", ondelete="CASCADE")
    exp: int
    is_blacklisted: bool = Field(default=False)

    user: "User" = Relationship(back_populates="tokens")

class User(SQLModel, table=True):
    __tablename__ = "Users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_group_id: int = Field(default=2, foreign_key="User_Groups.id", ondelete="SET NULL", nullable=True)
    firstname: str
    lastname: str
    username: str
    email: EmailStr = Field(unique=True)
    password: str
    is_active: bool = Field(default=False)
    creation_date: datetime
    modify_date: datetime

    ideas: List[Idea] = Relationship(back_populates="owner")
    tokens: List[User_Token] = Relationship(back_populates="user")
    feedback: List["User_Feedback"] = Relationship(back_populates="user")

class User_Activation(SQLModel, table=True):
    __tablename__ = "User_Activation"
    user_id: Optional[UUID] = Field(default=None, foreign_key="Users.id", ondelete="CASCADE")
    uuid: UUID = Field(primary_key=True)


class User_Group(SQLModel, table=True):
    __tablename__ = "User_Groups"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class ResetEmailValidation(SQLModel, table=True):
    __tablename__ = "Reset_Email_Validation"
    user_id: UUID = Field(foreign_key="Users.id", ondelete="CASCADE", primary_key=True)
    code: str
    ttl: datetime

class ResetPassword(SQLModel, table=True):
    __tablename__ = "Reset_Password"
    code: UUID = Field(primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="Users.id", ondelete="CASCADE")
    ttl: datetime
