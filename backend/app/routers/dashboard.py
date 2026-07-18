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

@router.get("/charts")
def get_dashboard_charts(db: Session = Depends(get_db)):
    """Returns aggregated datasets for rendering charts on the SOC dashboard."""
    from app import models
    from sqlalchemy import func
    from datetime import datetime
    
    # 1. Threat Trend (Alerts over time)
    trend_rows = (db.query(func.date(models.Alert.created_at), func.count(models.Alert.alert_id))
                  .group_by(func.date(models.Alert.created_at))
                  .order_by(func.date(models.Alert.created_at))
                  .all())
    threat_trend = [{"date": r[0], "count": r[1]} for r in trend_rows]
    
    if not threat_trend:
        threat_trend = [{"date": datetime.utcnow().strftime('%Y-%m-%d'), "count": 0}]

    # 2. User Risk Distribution (Histogram bins)
    risk_profiles = db.query(models.RiskProfile.latest_risk_score).all()
    bins = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }
    for rp in risk_profiles:
        score = rp[0] or 0.0
        if score <= 20:
            bins["0-20"] += 1
        elif score <= 40:
            bins["21-40"] += 1
        elif score <= 60:
            bins["41-60"] += 1
        elif score <= 80:
            bins["61-80"] += 1
        else:
            bins["81-100"] += 1
            
    risk_distribution = [{"range": k, "count": v} for k, v in bins.items()]

    # 3. Alerts by Severity (Pie Chart data)
    sev_rows = (db.query(models.Alert.severity, func.count(models.Alert.alert_id))
                  .group_by(models.Alert.severity)
                  .all())
    severity_breakdown = [{"name": r[0], "value": r[1]} for r in sev_rows]
    
    # 4. Hourly Activity (Event Volume)
    hour_rows = (db.query(models.Event.hour, func.count(models.Event.event_id))
                   .filter(models.Event.hour != None)
                   .group_by(models.Event.hour)
                   .order_by(models.Event.hour)
                   .all())
    hourly_activity = [{"hour": f"{int(r[0]):02d}:00", "events": r[1]} for r in hour_rows]

    return {
        "threat_trend": threat_trend,
        "risk_distribution": risk_distribution,
        "severity_breakdown": severity_breakdown,
        "hourly_activity": hourly_activity
    }