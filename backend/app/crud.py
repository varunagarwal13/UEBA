"""
crud.py
-------
CRUD = Create, Read, Update, Delete.
All database read/write logic lives here.
Routes call these functions — they don't touch the DB directly.
This separation makes code easier to test and change.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app import models, schemas
from datetime import datetime
from typing import List, Optional
import pandas as pd


# ── Users ─────────────────────────────────────────────────────────────────────

def get_or_create_user(db: Session, user_id: str, username: str = None,
                        department: str = None, role: str = None) -> models.User:
    """Fetch user if exists, create if not. Avoids duplicate entries."""
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        user = models.User(
            user_id    = user_id,
            username   = username or user_id,
            department = department,
            role       = role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def get_all_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()


# ── Events ────────────────────────────────────────────────────────────────────

def bulk_insert_events(db: Session, records: list):
    """
    Insert many events at once using bulk_insert_mappings.
    Much faster than inserting one-by-one for large CSVs.
    """
    db.bulk_insert_mappings(models.Event, records)
    db.commit()

def get_events_for_user(db: Session, user_id: str, limit: int = 200) -> List[models.Event]:
    return (db.query(models.Event)
              .filter(models.Event.user_id == user_id)
              .order_by(desc(models.Event.timestamp))
              .limit(limit)
              .all())

def get_events_for_ctmc(db: Session) -> pd.DataFrame:
    """
    Returns a DataFrame of all events sorted by user + timestamp.
    This is what Person 1 reads via GET /data/events.
    """
    rows = (db.query(
                models.Event.user_id,
                models.Event.timestamp,
                models.Event.ctmc_state,
                models.Event.event_type,
                models.Event.risk_score,
                models.Event.rules_triggered,
                models.Event.is_anomaly
            )
            .order_by(models.Event.user_id, models.Event.timestamp)
            .all())
    return pd.DataFrame(rows, columns=[
        "user_id","timestamp","ctmc_state","event_type",
        "risk_score","rules_triggered","is_anomaly"
    ])


# ── Network Events ────────────────────────────────────────────────────────────

def bulk_insert_network_events(db: Session, records: list):
    db.bulk_insert_mappings(models.NetworkEvent, records)
    db.commit()


# ── Analytics Results → Alerts ────────────────────────────────────────────────

def store_analytics_result(db: Session, result: schemas.AnalyticsResult) -> models.Alert:
    """
    Receives Person 1's risk result.
    1. Creates/updates the RiskProfile for the user.
    2. Creates an Alert if severity is High or Critical.
    """
    # Ensure user exists
    get_or_create_user(db, result.user_id)

    # Update or create risk profile
    profile = db.query(models.RiskProfile).filter(
        models.RiskProfile.user_id == result.user_id
    ).first()

    if profile:
        profile.latest_risk_score = result.risk_score
        profile.max_risk_score    = max(profile.max_risk_score, result.risk_score)
        profile.severity          = result.severity
        profile.total_alerts     += 1
        if result.severity in ("High", "Critical"):
            profile.open_alerts  += 1
        profile.last_seen         = datetime.utcnow()
    else:
        profile = models.RiskProfile(
            user_id           = result.user_id,
            latest_risk_score = result.risk_score,
            max_risk_score    = result.risk_score,
            severity          = result.severity,
            total_alerts      = 1,
            open_alerts       = 1 if result.severity in ("High","Critical") else 0,
            last_seen         = datetime.utcnow()
        )
        db.add(profile)

    # Create alert
    alert = models.Alert(
        user_id         = result.user_id,
        risk_score      = result.risk_score,
        severity        = result.severity,
        rules_triggered = result.rules_triggered,
        ctmc_log_prob   = result.ctmc_log_prob,
        explanation     = result.explanation,
        status          = "open"
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


# ── Alerts ────────────────────────────────────────────────────────────────────

def get_alerts(db: Session, severity: str = None,
               status: str = None, limit: int = 100) -> List[models.Alert]:
    q = db.query(models.Alert)
    if severity:
        q = q.filter(models.Alert.severity == severity)
    if status:
        q = q.filter(models.Alert.status == status)
    return q.order_by(desc(models.Alert.created_at)).limit(limit).all()

def update_alert_status(db: Session, alert_id: int, new_status: str) -> Optional[models.Alert]:
    alert = db.query(models.Alert).filter(models.Alert.alert_id == alert_id).first()
    if alert:
        alert.status = new_status
        db.commit()
        db.refresh(alert)
    return alert


# ── Risk Profiles ─────────────────────────────────────────────────────────────

def get_risk_profiles(db: Session, limit: int = 50) -> List[models.RiskProfile]:
    return (db.query(models.RiskProfile)
              .order_by(desc(models.RiskProfile.latest_risk_score))
              .limit(limit).all())


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard_metrics(db: Session) -> dict:
    total_users   = db.query(func.count(models.User.user_id)).scalar()
    total_events  = db.query(func.count(models.Event.event_id)).scalar()
    total_alerts  = db.query(func.count(models.Alert.alert_id)).scalar()
    open_alerts   = db.query(func.count(models.Alert.alert_id)).filter(
                        models.Alert.status == "open").scalar()
    critical      = db.query(func.count(models.Alert.alert_id)).filter(
                        models.Alert.severity == "Critical").scalar()
    high          = db.query(func.count(models.Alert.alert_id)).filter(
                        models.Alert.severity == "High").scalar()
    anomaly_count = db.query(func.count(models.Event.event_id)).filter(
                        models.Event.is_anomaly == True).scalar()
    anomaly_rate  = round((anomaly_count / total_events * 100), 2) if total_events else 0

    # Alerts grouped by severity
    sev_rows = (db.query(models.Alert.severity, func.count(models.Alert.alert_id))
                  .group_by(models.Alert.severity).all())
    alerts_by_severity = {row[0]: row[1] for row in sev_rows}

    # Events grouped by type
    type_rows = (db.query(models.Event.event_type, func.count(models.Event.event_id))
                   .group_by(models.Event.event_type).all())
    events_by_type = {row[0]: row[1] for row in type_rows}

    # Top 10 riskiest users
    top_risky = (db.query(models.RiskProfile)
                   .order_by(desc(models.RiskProfile.latest_risk_score))
                   .limit(10).all())

    return {
        "total_users":        total_users,
        "total_events":       total_events,
        "total_alerts":       total_alerts,
        "open_alerts":        open_alerts,
        "critical_alerts":    critical,
        "high_alerts":        high,
        "anomaly_rate_pct":   anomaly_rate,
        "top_risky_users":    top_risky,
        "alerts_by_severity": alerts_by_severity,
        "events_by_type":     events_by_type,
    }