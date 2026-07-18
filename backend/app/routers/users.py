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

@router.get("/{user_id}/history")
def get_user_history(user_id: str, db: Session = Depends(get_db)):
    """Returns the historical session profile, alerts count, and previous alerts list for a user."""
    from app import models
    from sqlalchemy import desc
    
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(404, f"User {user_id} not found.")
        
    profile = db.query(models.RiskProfile).filter(models.RiskProfile.user_id == user_id).first()
    
    alerts = (db.query(models.Alert)
              .filter(models.Alert.user_id == user_id)
              .order_by(desc(models.Alert.created_at))
              .all())
              
    events_count = db.query(models.Event).filter(models.Event.user_id == user_id).count()
    
    return {
        "user_id": user_id,
        "username": user.username,
        "department": user.department,
        "role": user.role,
        "email": user.email,
        "is_active": user.is_active,
        "risk_profile": {
            "latest_risk_score": profile.latest_risk_score if profile else 0.0,
            "max_risk_score": profile.max_risk_score if profile else 0.0,
            "severity": profile.severity if profile else "Low",
            "total_alerts": profile.total_alerts if profile else 0,
            "open_alerts": profile.open_alerts if profile else 0,
        } if profile else None,
        "total_events": events_count,
        "alerts": [
            {
                "alert_id": a.alert_id,
                "risk_score": a.risk_score,
                "severity": a.severity,
                "status": a.status,
                "rules_triggered": a.rules_triggered,
                "created_at": a.created_at
            }
            for a in alerts
        ]
    }