from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Annotated

app = FastAPI()


@app.get("/")
async def root():
    t = "Test Var"
    return {"message": "Hello World"}


@app.get("/test/")
async def root(val: Annotated[str | None, Query(max_length=10) ] = None):
    return {val}


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.put("/items/")
async def create_item(item: Item):
    return item