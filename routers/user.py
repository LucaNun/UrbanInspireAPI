from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def get_users():
    return {"message": "List of users"}
