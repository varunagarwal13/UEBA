from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas
from typing import List

router = APIRouter(tags=["Risk"])

@router.get("/risk", response_model=List[schemas.RiskProfileOut])
def get_risk_profiles(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Returns all user risk profiles sorted by highest risk score.
    Person 3 uses this for the risk leaderboard on the dashboard.
    """
    return crud.get_risk_profiles(db, limit=limit)


@router.post("/analytics/results", summary="Receive analytics from Person 1")
def receive_analytics_results(
    payload: schemas.AnalyticsResultBatch,
    db: Session = Depends(get_db)
):
    """
    Person 1's ML engine POSTs results here after running the CTMC model.
    Backend stores the results and auto-generates alerts for High/Critical users.

    Example payload:
    {
      "results": [
        {"user_id": "USR001", "risk_score": 92.0, "severity": "Critical",
         "rules_triggered": "Beaconing|Privilege_Escalation",
         "explanation": "Netcat usage followed by file deletion"}
      ]
    }
    """
    created_alerts = []
    for result in payload.results:
        alert = crud.store_analytics_result(db, result)
        created_alerts.append(alert.alert_id)

    return {
        "status":         "stored",
        "alerts_created": len(created_alerts),
        "alert_ids":      created_alerts
    }