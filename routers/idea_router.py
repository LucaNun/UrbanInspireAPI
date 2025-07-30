from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from typing import Annotated 
import shutil, json
from uuid import uuid4
from datetime import datetime
from fastapi_limiter.depends import RateLimiter

from sql_app import schemas, crud as db
from sql_app.database import get_db_session
from sql_app.models import Idea, Idea_Image, Image_To_Idea, Idea_Likes, Idea_Status
from utils import auth

router = APIRouter()

@router.post("/", dependencies=[Depends(RateLimiter(times=1, seconds=30, identifier=auth.get_identifyer_for_limiter))])
async def create_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],new_idea: schemas.Idea, session: Session = Depends(get_db_session)):
    new_idea = schemas.Idea_Create(**new_idea.model_dump(), owner_id=current_user.id)
    new_idea = Idea(**new_idea.model_dump())
    new_idea.creation_date = datetime.now()
    new_idea.modify_date = datetime.now()
    session.add(new_idea)
    session.commit()
    session.refresh(new_idea)
    return {"status": True, "idea_id": new_idea.id}


@router.post("/uploadImage", dependencies=[Depends(RateLimiter(times=20, seconds=30, identifier=auth.get_identifyer_for_limiter))])
async def upload_image(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],image: UploadFile, image_name: str = Form(), idea_id: int = Form(), session: Session = Depends(get_db_session)):
    idea = session.get(Idea, idea_id)
    if idea.owner_id != current_user.id:
        return HTTPException(status_code=401, detail="You are not the owner!")
    
    if not image.filename.endswith(".jpg"):
        return HTTPException(status_code=400, detail="False image format! Use one of the following: .jpg")
    
    filename = str(uuid4())
    filename += ".jpg"
    with open("images/" + filename, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    new_image = Idea_Image(user_id=current_user.id, name=image_name, image_path=filename)
    
    session.add(new_image)
    session.commit()
    session.refresh(new_image)
    
    link = Image_To_Idea(image_id=new_image.id, idea_id=idea_id)
    session.add(link)
    session.commit()
    session.refresh(link)

    return {"status": True}


@router.patch("/", dependencies=[Depends(RateLimiter(times=1, seconds=20, identifier=auth.get_identifyer_for_limiter))])
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


@router.delete("/", dependencies=[Depends(RateLimiter(times=1, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def delete_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: int = Form(),session: Session = Depends(get_db_session)):
    idea = session.get(Idea, id)
    
    if not idea:
        return HTTPException(status_code=404, detail="Idea not found!")
    
    if current_user.id != idea.owner_id:
        return HTTPException(status_code=401, detail="You are not the owner!")
    
    session.delete(idea)
    session.commit()

    return {"status": True}


@router.get("/{id}", dependencies=[Depends(RateLimiter(times=30, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def get_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],id: int, session: Session = Depends(get_db_session)):
    idea = session.get(Idea, id)
    
    if not idea:
        return HTTPException(status_code=404, detail="Idea not found!")

    status = session.get(Idea_Status, idea.status_id)
    images = idea.images
    idea = json.loads(idea.model_dump_json())
    idea["images"] = images
    idea["status_name"] = status.name

    return idea


@router.get("/ideas/", dependencies=[Depends(RateLimiter(times=50, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def get_ideas(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], sortdesc: bool = False, lastID: int = None, status: list[int] = Query(), session: Session = Depends(get_db_session)):  
    if not lastID:
        if sortdesc:
            statement = select(Idea.id).order_by(Idea.id.desc()).limit(1)
        else:
            statement = select(Idea.id).order_by(Idea.id.asc()).limit(1)
        lastID = session.exec(statement).first()
    if sortdesc:
        statement = select(Idea.id).where(Idea.status_id.in_(status)).where(Idea.id <= lastID).order_by(Idea.creation_date.desc()).limit(10)
    else:
        statement = select(Idea.id).where(Idea.status_id.in_(status)).where(Idea.id >= lastID).order_by(Idea.creation_date.asc()).limit(10)
    ids = session.exec(statement).all()
    
    allIdeas = []
    for x, id in enumerate(ids):
        idea = session.get(Idea, id)
        allIdeas.append(json.loads(idea.model_dump_json()))
        allIdeas[x]["images"] = idea.images

    return allIdeas


@router.get("/image/{imagename}", dependencies=[Depends(RateLimiter(times=100, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def get_image(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], imagename: str, session: Session = Depends(get_db_session)):
    return FileResponse("images/" + imagename)

@router.get("/{id}/like", dependencies=[Depends(RateLimiter(times=10, seconds=20, identifier=auth.get_identifyer_for_limiter))])
def get_like_for_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: int, session: Session = Depends(get_db_session)):
    like = session.get(Idea_Likes, [id, current_user.id])
    
    if not like:
        return {"like": like}
    return {"like": like.like}

@router.post("/{id}/like", dependencies=[Depends(RateLimiter(times=50, seconds=10, identifier=auth.get_identifyer_for_limiter))])
def update_like_for_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: int, like: bool = Form(), session: Session = Depends(get_db_session)):
    idea = session.get(Idea, id)
    if not idea:
        return HTTPException(status_code=404, detail="Idea not found!")
        
    liked = session.get(Idea_Likes, [id, current_user.id])
    
    if liked:
        if like == liked.like:
            pass
        else:
            liked.like = like
            session.commit()
    else:
        like = Idea_Likes(idea_id=id, user_id=current_user.id, like=like)
        session.add(like)
        session.commit() 
        
    return {"status": True}

@router.delete("/{id}/like", dependencies=[Depends(RateLimiter(times=10, seconds=20, identifier=auth.get_identifyer_for_limiter))])
def delete_like_for_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: int, session: Session = Depends(get_db_session)):
    like = session.get(Idea_Likes, [id, current_user.id])
    if like:
        session.delete(like)
        session.commit()
    else:
        return HTTPException(status_code=404, detail="Like not found!")
    
    return {"status": True}