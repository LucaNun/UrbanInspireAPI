from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select, func
from sqlalchemy import cast
from sqlalchemy.orm import selectinload
from typing import Annotated
import shutil, json, os
from uuid import UUID
from datetime import datetime
from utils.rate_limiter import rate_limited
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from sql_app import schemas, crud as db
from sql_app.database import get_db_session
from sql_app.models import Idea, Idea_Image, Image_To_Idea, Idea_Likes, Idea_Status, Idea_Categories
from utils import auth

router = APIRouter()

@router.post("/", dependencies=rate_limited("idea:create", 3, 10, auth.get_identifyer_for_limiter))
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


@router.post("/uploadImage", dependencies=rate_limited("idea:upload_image", 20, 30, auth.get_identifyer_for_limiter))
async def upload_image(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],image: UploadFile, image_name: str = Form(), idea_id: UUID = Form(), session: Session = Depends(get_db_session)):
    idea = session.get(Idea, idea_id)
    if idea.owner_id != current_user.id:
        raise HTTPException(status_code=401, detail="You are not the owner!")

    if not image.filename.endswith(".webp") or image.content_type != "image/webp":
        raise HTTPException(status_code=400, detail="False image format! Use one of the following: .webp")

    header = await image.read(12)
    await image.seek(0)
    if not (header[:4] == b'RIFF' and header[8:12] == b'WEBP'):
        raise HTTPException(status_code=400, detail="File content is not a valid WebP image.")

    new_image = Idea_Image(user_id=current_user.id, name=image_name)

    with open(f"images/{new_image.id}.webp", "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    session.add(new_image)
    session.commit()
    session.refresh(new_image)

    link = Image_To_Idea(image_id=new_image.id, idea_id=idea_id)
    session.add(link)
    session.commit()
    session.refresh(link)

    return {"status": True}


@router.patch("/", dependencies=rate_limited("idea:update", 2, 10, auth.get_identifyer_for_limiter))
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


@router.delete("/", dependencies=rate_limited("idea:delete", 4, 30, auth.get_identifyer_for_limiter))
def delete_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: UUID = Form(),session: Session = Depends(get_db_session)):
    idea = session.get(Idea, id)

    if not idea:
        return HTTPException(status_code=404, detail="Idea not found!")

    if current_user.id != idea.owner_id:
        return HTTPException(status_code=401, detail="You are not the owner!")

    session.delete(idea)
    session.commit()

    return {"status": True}

@router.get("/categorys", dependencies=rate_limited("idea:categories", 30, 60, auth.get_identifyer_for_limiter))
def get_idea_categorys(session: Session = Depends(get_db_session)):
    statement = (
        select(
            Idea_Categories.name,
            Idea_Categories.id,
            (func.count(Idea.id) * 100.0 / select(func.count(Idea.id)).select_from(Idea)).label("percentage")
        )
        .select_from(Idea_Categories)
        .outerjoin(Idea, Idea.category_id == Idea_Categories.id)
        .group_by(Idea_Categories.id, Idea_Categories.name)
    )
    categorys = session.exec(statement).all()
    categorys = [schemas.IdeaCategoryWithUsage(name=row[0], id=row[1], usage=row[2]) for row in categorys]
    return categorys

@router.get("/ideas/nearby", response_model=list[schemas.IdeaNearbyItem], dependencies=rate_limited("idea:nearby", 30, 60, auth.get_identifyer_for_limiter))
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


@router.get("/{id}", dependencies=rate_limited("idea:get", 30, 60, auth.get_identifyer_for_limiter))
def get_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)],id: UUID, session: Session = Depends(get_db_session)):
    idea = session.get(Idea, id)

    if not idea:
        return HTTPException(status_code=404, detail="Idea not found!")

    images = idea.images
    cat = session.get(Idea_Categories, idea.category_id)
    idea = json.loads(idea.model_dump_json())
    idea["images"] = images
    idea["category_name"] = cat.name

    return idea


@router.get("/ideas/", response_model=list[schemas.IdeaBase], dependencies=rate_limited("idea:list", 50, 60, auth.get_identifyer_for_limiter))
def get_ideas(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], sortdesc: bool = False, lastID: UUID | None = None, status: list[int] = Query(), category: list[int] | None = Query(default=None), session: Session = Depends(get_db_session)):
    statement = (
        select(Idea)
        .options(selectinload(Idea.images))
        .join(Idea_Status, Idea.status_id == Idea_Status.id)
        .where(Idea_Status.public == True)
        .where(Idea.status_id.in_(status))
    )

    if category:
        statement = statement.where(Idea.category_id.in_(category))

    if lastID is not None:
        last_creation_date = (
            select(Idea.creation_date)
            .where(Idea.id == lastID)
            .scalar_subquery()
        )
        if sortdesc:
            statement = statement.where(Idea.creation_date < last_creation_date)
        else:
            statement = statement.where(Idea.creation_date > last_creation_date)

    if sortdesc:
        statement = statement.order_by(Idea.creation_date.desc())
    else:
        statement = statement.order_by(Idea.creation_date.asc())

    ideas = session.exec(statement.limit(10)).all()

    return [
        schemas.IdeaBase(**idea.model_dump(exclude={"location"}), images=[img.model_dump() for img in idea.images])
        for idea in ideas
    ]

@router.get("/ideas/status", dependencies=rate_limited("idea:status", 50, 10, auth.get_identifyer_for_limiter))
def get_ideas( session: Session = Depends(get_db_session)) -> list[schemas.IdeasStatus]:
    statement = select(Idea_Status).where(Idea_Status.public)
    status = session.exec(statement)
    return status


@router.get("/image/{image_id}", dependencies=rate_limited("idea:image", 100, 20, auth.get_identifyer_for_limiter))
def get_image(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], image_id: UUID, session: Session = Depends(get_db_session)):
    path = os.path.join("images", f"{image_id}.webp")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(path)

@router.get("/{id}/like", dependencies=rate_limited("idea:like_get", 50, 10, auth.get_identifyer_for_limiter))
def get_like_for_user_and_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: UUID, session: Session = Depends(get_db_session)):
    like = session.get(Idea_Likes, [id, current_user.id])

    if not like:
        return {"like": like}
    return {"like": like.like}

@router.get("/{id}/likes", dependencies=rate_limited("idea:likes_count", 50, 10, auth.get_identifyer_for_limiter))
def get_likes_for_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: UUID, session: Session = Depends(get_db_session)):
    statement = select(
        func.count(Idea_Likes.user_id).filter(Idea_Likes.like == True).label("likes"),
        func.count(Idea_Likes.user_id).filter(Idea_Likes.like == False).label("dislikes")
    ).where(Idea_Likes.idea_id == id)
    result = session.exec(statement).first()

    return {"likes": result.likes, "dislikes": result.dislikes}

@router.post("/{id}/like", dependencies=rate_limited("idea:like_set", 30, 10, auth.get_identifyer_for_limiter))
def update_like_for_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: UUID, like: bool = Form(), session: Session = Depends(get_db_session)):
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

@router.delete("/{id}/like", dependencies=rate_limited("idea:like_delete", 30, 10, auth.get_identifyer_for_limiter))
def delete_like_for_idea(current_user: Annotated[schemas.User, Depends(auth.get_current_active_user)], id: UUID, session: Session = Depends(get_db_session)):
    like = session.get(Idea_Likes, [id, current_user.id])
    if like:
        session.delete(like)
        session.commit()
    else:
        return HTTPException(status_code=404, detail="Like not found!")

    return {"status": True}
