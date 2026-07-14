from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas
from typing import List, Optional

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[schemas.AlertOut])
def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by: Low/Medium/High/Critical"),
    status:   Optional[str] = Query(None, description="Filter by: open/reviewed/closed"),
    limit:    int           = Query(100,  description="Max records to return"),
    db: Session = Depends(get_db)
):
    """
    Person 3 calls this to populate the alerts table in the SOC dashboard.
    Supports optional filtering by severity and status.
    """
    return crud.get_alerts(db, severity=severity, status=status, limit=limit)

@router.patch("/{alert_id}/status", response_model=schemas.AlertOut)
def update_alert_status(
    alert_id: int,
    update: schemas.AlertStatusUpdate,
    db: Session = Depends(get_db)
):
    """SOC analyst marks alert as reviewed or closed."""
    alert = crud.update_alert_status(db, alert_id, update.status)
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(404, f"Alert {alert_id} not found.")
    return alert