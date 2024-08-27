from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from uuid import UUID
from datetime import timedelta

class Item(SQLModel, table=True):
    __tablename__ = "Items"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    owner_id: Optional[int] = Field(default=None, foreign_key="Users.id")

    owner: "User" = Relationship(back_populates="items")
class User_Token(SQLModel, table=True):
    __tablename__ = "User_Token"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None,foreign_key="Users.id")
    uuid: UUID
    exp: int
    
    user: "User" = Relationship(back_populates="tokens")
    blacklist: "User_Token_Blacklist" = Relationship(back_populates="token")
    
class User_Token_Blacklist(SQLModel, table=True):
    __tablename__ = "User_Token_Blacklist"
    id: Optional[int] = Field(default=None, primary_key=True)
    token_id: int = Field(foreign_key="User_Token.id")
    
    token: User_Token = Relationship(back_populates="blacklist")
    
class User(SQLModel, table=True):
    __tablename__ = "Users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    password: str
    is_active: bool = Field(default=True)

    items: List[Item] = Relationship(back_populates="owner")
    tokens: List[User_Token] = Relationship(back_populates="user")

