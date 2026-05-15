from fastapi import APIRouter, Depends
from app.schemas.schemas import UserOut
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
