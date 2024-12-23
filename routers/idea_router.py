from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlmodel import Session, select
from typing import Annotated 
import shutil
from datetime import datetime

from sql_app import schemas, crud as db
from sql_app.database import get_db_session
from sql_app.models import Idea, Idea_Image, Image_To_Idea
from utils import auth

router = APIRouter()

@router.post("/")
async def create_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],new_idea: schemas.Idea, session: Session = Depends(get_db_session)):
    new_idea = schemas.Idea_Create(**new_idea.model_dump(), owner_id=current_user.id)
    new_idea = Idea(**new_idea.model_dump())
    session.add(new_idea)
    session.commit()
    session.refresh(new_idea)
    return {"status": True, "idea_id": new_idea.id}

@router.post("/uploadImage")
async def upload_image(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],image: UploadFile, image_name: str = Form(), idea_id: int = Form(), session: Session = Depends(get_db_session)):
    
    if image.filename.endswith(".wrt"):
        return HTTPException(status_code=400, detail="False image format")
    
    # Nochmal den Pfad ändern und filename generieren
    with open(image.filename, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    new_image = Idea_Image(user_id=current_user.id, name=image_name, image_path=image.filename)
    
    session.add(new_image)
    session.commit()
    session.refresh(new_image)
    
    link = Image_To_Idea(image_id=new_image.id, idea_id=idea_id)
    session.add(link)
    session.commit()
    session.refresh(link)

    return {"status": True}


@router.patch("/")
def update_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], update_items: schemas.IdeaUpdate, session: Session = Depends(get_db_session)):
    idea = session.get(Idea, update_items.id)
    
    if current_user.id != idea.owner_id:
        return HTTPException(status_code=401, detail="You are not the owner!")
    
    
    update_data = update_items.model_dump(exclude_unset=True)
    
    idea.sqlmodel_update(update_data)
    idea.modify_date = datetime.now()
    session.add(idea)
    session.commit()
    session.refresh(idea)
    
    return {"status": True}

@router.delete("/")
def delete_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: int = Form(),session: Session = Depends(get_db_session)):
    idea = session.get(Idea, id)
    
    if not idea:
        return HTTPException(status_code=404, detail="Idea not found!")
    
    if current_user.id != idea.owner_id:
        return HTTPException(status_code=401, detail="You are not the owner!")
    
    session.delete(idea)
    session.commit()

    return {"ok": True}


@router.get("/{id}")
def get_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],id: int, session: Session = Depends(get_db_session)):
    idea = session.get(Idea, id)
    
    if not idea:
        return HTTPException(status_code=404, detail="Idea not found!")
    
    subquery = select(Image_To_Idea.image_id).where(Image_To_Idea.idea_id == id)
    statement = select(Idea_Image).where(Idea_Image.id.in_(subquery))
    images = session.exec(statement).all()
     
    if not images:
        return idea
    
    return idea, images