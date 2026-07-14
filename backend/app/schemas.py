"""
schemas.py
----------
Pydantic models — define what data comes IN to your API (requests)
and what goes OUT (responses). FastAPI uses these for:
  - Automatic input validation
  - Auto-generated /docs UI
  - Type checking at runtime

These are NOT database tables. They're just data shapes for the API layer.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── User ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    user_id:    str
    username:   str
    department: Optional[str] = None
    role:       Optional[str] = None
    email:      Optional[str] = None

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    is_active:  bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Events ───────────────────────────────────────────────────────────────────

class EventOut(BaseModel):
    event_id:   int
    user_id:    str
    timestamp:  Optional[datetime]
    event_type: str
    ctmc_state: Optional[str]
    risk_score: float
    is_anomaly: bool
    rules_triggered: Optional[str]

    class Config:
        from_attributes = True


# ── Analytics Results (Person 1 → Backend) ───────────────────────────────────

class AnalyticsResult(BaseModel):
    """
    Shape of what Person 1 sends back after running the Markov model.
    Backend stores this and creates an alert if severity is High/Critical.
    """
    user_id:         str
    risk_score:      float = Field(..., ge=0, le=100)
    severity:        str   = Field(..., pattern="^(Low|Medium|High|Critical)$")
    rules_triggered: Optional[str] = None
    ctmc_log_prob:   Optional[float] = None
    explanation:     Optional[str] = None

class AnalyticsResultBatch(BaseModel):
    """Send multiple results at once."""
    results: List[AnalyticsResult]


# ── Alerts ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    alert_id:   int
    user_id:    str
    risk_score: float
    severity:   str
    status:     str
    rules_triggered: Optional[str]
    explanation:     Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class AlertStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|reviewed|closed)$")


# ── Risk Profiles ─────────────────────────────────────────────────────────────

class RiskProfileOut(BaseModel):
    user_id:           str
    latest_risk_score: float
    max_risk_score:    float
    severity:          str
    total_alerts:      int
    open_alerts:       int
    total_events:      int
    anomaly_events:    int
    last_seen:         Optional[datetime]

    class Config:
        from_attributes = True


# ── Dashboard ────────────────────────────────────────────────────────────────

class DashboardMetrics(BaseModel):
    """Summary metrics for Person 3's SOC dashboard."""
    total_users:        int
    total_events:       int
    total_alerts:       int
    open_alerts:        int
    critical_alerts:    int
    high_alerts:        int
    anomaly_rate_pct:   float
    top_risky_users:    List[RiskProfileOut]
    alerts_by_severity: dict
    events_by_type:     dict