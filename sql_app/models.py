from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List

class Item(SQLModel, table=True):
    __tablename__ = "Items"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    owner_id: Optional[int] = Field(default=None, foreign_key="Users.id")

    owner: "User" = Relationship(back_populates="items")

class User(SQLModel, table=True):
    __tablename__ = "Users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    password: str
    is_active: bool = Field(default=True)

    items: List[Item] = Relationship(back_populates="owner")
