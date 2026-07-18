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

@router.get("/{alert_id}")
def get_alert_detail(alert_id: int, db: Session = Depends(get_db)):
    """Fetch details of a single alert, parsing the JSON explanation if present."""
    from app import models
    import json
    
    alert = db.query(models.Alert).filter(models.Alert.alert_id == alert_id).first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(404, f"Alert {alert_id} not found.")
    
    parsed_explanation = None
    if alert.explanation:
        try:
            parsed_explanation = json.loads(alert.explanation)
        except Exception:
            parsed_explanation = alert.explanation
            
    return {
        "alert_id": alert.alert_id,
        "user_id": alert.user_id,
        "risk_score": alert.risk_score,
        "severity": alert.severity,
        "status": alert.status,
        "rules_triggered": alert.rules_triggered,
        "ctmc_log_prob": alert.ctmc_log_prob,
        "created_at": alert.created_at,
        "explanation": parsed_explanation
    }