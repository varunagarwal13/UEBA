from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("", response_model=schemas.DashboardMetrics)
def get_dashboard(db: Session = Depends(get_db)):
    """
    Single endpoint that returns all summary metrics Person 3 needs
    to render the SOC dashboard without making multiple API calls.

    Returns: user count, event count, alert breakdown,
             anomaly rate, top risky users, event type distribution.
    """
    return crud.get_dashboard_metrics(db)