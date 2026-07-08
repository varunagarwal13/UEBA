from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas
from typing import List

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("", response_model=List[schemas.UserOut])
def get_users(db: Session = Depends(get_db)):
    """Returns all users. Person 3 uses this to populate user dropdowns."""
    return crud.get_all_users(db)