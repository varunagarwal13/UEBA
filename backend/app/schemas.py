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
from typing import Optional, List, Dict
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
    ctmc_log_prob:   Optional[float] = None
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

# ── V2.1 OUT ──────────────────────────────────────────────────────────────────

class ChainStageOut(BaseModel):
    stage:      str
    session_id: Optional[str] = None
    timestamp:  Optional[datetime] = None
    evidence:   Optional[str] = None

class AttackChainOut(BaseModel):
    chain_id:      str
    user_id:       str
    first_seen:    Optional[datetime]
    last_seen:     Optional[datetime]
    current_stage: Optional[str]
    stages:        List[ChainStageOut]
    sessions:      List[str]
    risk_score:    float
    confidence:    float
    status:        str

class CaseOut(BaseModel):
    case_id:       str
    user_id:       str
    status:        str
    risk_score:    float
    severity:      str
    current_stage: Optional[str]
    summary:       Optional[str]
    alert_ids:     List[int]
    chain_id:      Optional[str] = None
    created_at:    Optional[datetime]
    updated_at:    Optional[datetime]

class FeatureStatOut(BaseModel):
    mean:    float
    std:     float
    current: float          # peak observed value — the profile keeps no per-session history
    min:     float
    count:   int

class BehaviorProfileOut(BaseModel):
    user_id:            str
    profile_version:    int
    session_count:      int
    confidence:         float
    state_distribution: Dict[str, float]
    statistics:         Dict[str, FeatureStatOut]
    hourly:             List[List[int]]
