from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select, func
from sqlalchemy import cast
from typing import Annotated
import shutil, json, os
from uuid import uuid4
from datetime import datetime
from fastapi_limiter.depends import RateLimiter
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from sql_app import schemas, crud as db
from sql_app.database import get_db_session
from sql_app.models import Idea, Idea_Image, Image_To_Idea, Idea_Likes, Idea_Status, Idea_Categorys
from utils import auth

router = APIRouter()

@router.post("/", dependencies=[Depends(RateLimiter(times=1, seconds=30, identifier=auth.get_identifyer_for_limiter))])
async def create_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],new_idea: schemas.GetCreateIdea, session: Session = Depends(get_db_session)):
    new_idea = schemas.Idea_Create(**new_idea.model_dump(), owner_id=current_user.id)
    new_idea = Idea(**new_idea.model_dump())
    new_idea.creation_date = datetime.now()
    new_idea.modify_date = datetime.now()
    new_idea.location = from_shape(Point(new_idea.longitude, new_idea.latitude), srid=4326)
    session.add(new_idea)
    session.commit()
    session.refresh(new_idea)
    return {"status": True, "idea_id": new_idea.id}


@router.post("/uploadImage", dependencies=[Depends(RateLimiter(times=20, seconds=30, identifier=auth.get_identifyer_for_limiter))])
async def upload_image(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],image: UploadFile, image_name: str = Form(), idea_id: int = Form(), session: Session = Depends(get_db_session)):
    idea = session.get(Idea, idea_id)
    if idea.owner_id != current_user.id:
        raise HTTPException(status_code=401, detail="You are not the owner!")
    
    if not image.filename.endswith(".webp") or image.content_type != "image/webp":
        raise HTTPException(status_code=400, detail="False image format! Use one of the following: .webp")

    header = await image.read(12)
    await image.seek(0)
    if not (header[:4] == b'RIFF' and header[8:12] == b'WEBP'):
        raise HTTPException(status_code=400, detail="File content is not a valid WebP image.")

    filename = str(uuid4())
    filename += ".webp"
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
    if update_items.latitude is not None or update_items.longitude is not None:
        idea.location = from_shape(Point(idea.longitude, idea.latitude), srid=4326)
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

@router.get("/categorys", dependencies=[Depends(RateLimiter(times=30, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def get_idea_categorys(session: Session = Depends(get_db_session)):
    statement = (
        select(
            Idea_Categorys.name,
            Idea_Categorys.id,
            (func.count(Idea.id) * 100.0 / select(func.count(Idea.id)).select_from(Idea)).label("percentage")
        )
        .select_from(Idea_Categorys)
        .outerjoin(Idea, Idea.category_id == Idea_Categorys.id)
        .group_by(Idea_Categorys.id, Idea_Categorys.name)
    )
    categorys = session.exec(statement).all()
    categorys = [schemas.IdeaCategoryWithUsage(name=row[0], id=row[1], usage=row[2]) for row in categorys]
    return categorys

@router.get("/ideas/nearby", response_model=list[schemas.IdeaNearbyItem], dependencies=[Depends(RateLimiter(times=30, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def get_ideas_nearby(
    current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: float = Query(..., gt=0, le=200),
    status: list[int] = Query(),
    category: list[int] | None = Query(default=None),
    session: Session = Depends(get_db_session)
):
    user_point = cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), Geography)
    distance_expr = ST_Distance(Idea.location, user_point).label("distance_m")

    statement = (
        select(Idea, distance_expr)
        .where(Idea.location.isnot(None))
        .where(ST_DWithin(Idea.location, user_point, radius * 1000))
        .where(Idea.status_id.in_(status))
        .order_by(distance_expr)
        .limit(100)
    )
    if category:
        statement = statement.where(Idea.category_id.in_(category))
    rows = session.exec(statement).all()

    result = []
    for idea, distance_m in rows:
        result.append(schemas.IdeaNearbyItem(
            **idea.model_dump(exclude={"location"}),
            images=[image.model_dump() for image in idea.images],
            distance_km=round(distance_m / 1000, 2),
        ))
    return result


@router.get("/{id}", dependencies=[Depends(RateLimiter(times=30, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def get_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],id: int, session: Session = Depends(get_db_session)):
    idea = session.get(Idea, id)
    
    if not idea:
        return HTTPException(status_code=404, detail="Idea not found!")

    images = idea.images
    cat = session.get(Idea_Categorys, idea.category_id)
    idea = json.loads(idea.model_dump_json())
    idea["images"] = images
    idea["category_name"] = cat.name

    return idea


@router.get("/ideas/", response_model=list[schemas.IdeaBase], dependencies=[Depends(RateLimiter(times=50, seconds=60, identifier=auth.get_identifyer_for_limiter))])
def get_ideas(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], sortdesc: bool = False, lastID: int = None, status: list[int] = Query(), category: list[int] | None = Query(default=None), session: Session = Depends(get_db_session)):
    if lastID is None:
        order = Idea.id.desc() if sortdesc else Idea.id.asc()
        lastID = session.exec(select(Idea.id).order_by(order).limit(1)).first()
    
    statement = select(Idea.id).where(Idea.status_id.in_(status))

    if category:
        statement = statement.where(Idea.category_id.in_(category))
        
    if sortdesc:
        statement = statement.where(Idea.id <= lastID).order_by(Idea.creation_date.desc())
    else:
        statement = statement.where(Idea.id >= lastID).order_by(Idea.creation_date.asc())

    statement = statement.limit(10)
    ids = session.exec(statement).all()
    
    allIdeas = []
    for x, id in enumerate(ids):
        idea = session.get(Idea, id)
        status = session.get(Idea_Status, idea.status_id)
        if not status.public:
            continue
        images = [image.model_dump() for image in idea.images]  
        idea =  schemas.IdeaBase(**idea.model_dump(exclude={"location"}), images=images)
        allIdeas.append(idea)

    return allIdeas

@router.get("/ideas/status", dependencies=[Depends(RateLimiter(times=50, seconds=10, identifier=auth.get_identifyer_for_limiter))])
def get_ideas( session: Session = Depends(get_db_session)) -> list[schemas.IdeasStatus]:
    statement = select(Idea_Status).where(Idea_Status.public)
    status = session.exec(statement)
    return status


@router.get("/image/{imagename}", dependencies=[Depends(RateLimiter(times=100, seconds=20, identifier=auth.get_identifyer_for_limiter))])
def get_image(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], imagename: str, session: Session = Depends(get_db_session)):
    safe_name = os.path.basename(imagename)
    path = os.path.join("images", safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(path)

@router.get("/{id}/like", dependencies=[Depends(RateLimiter(times=50, seconds=10, identifier=auth.get_identifyer_for_limiter))])
def get_like_for_user_and_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: int, session: Session = Depends(get_db_session)):
    like = session.get(Idea_Likes, [id, current_user.id])
    
    if not like:
        return {"like": like}
    return {"like": like.like}

@router.get("/{id}/likes", dependencies=[Depends(RateLimiter(times=50, seconds=10, identifier=auth.get_identifyer_for_limiter))])
def get_likes_for_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: int, session: Session = Depends(get_db_session)):
    statement = select(
        func.count(Idea_Likes.user_id).filter(Idea_Likes.like == True).label("likes"),
        func.count(Idea_Likes.user_id).filter(Idea_Likes.like == False).label("dislikes")
    ).where(Idea_Likes.idea_id == id)
    result = session.exec(statement).first()

    return {"likes": result.likes, "dislikes": result.dislikes}

@router.post("/{id}/like", dependencies=[Depends(RateLimiter(times=30, seconds=10, identifier=auth.get_identifyer_for_limiter))])
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

@router.delete("/{id}/like", dependencies=[Depends(RateLimiter(times=30, seconds=10, identifier=auth.get_identifyer_for_limiter))])
def delete_like_for_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: int, session: Session = Depends(get_db_session)):
    like = session.get(Idea_Likes, [id, current_user.id])
    if like:
        session.delete(like)
        session.commit()
    else:
        return HTTPException(status_code=404, detail="Like not found!")
    
    return {"status": True}