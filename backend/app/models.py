"""
models.py
---------
Defines all database tables as Python classes.
Each class = one table. Each class attribute = one column.

SQLAlchemy maps these to SQL CREATE TABLE statements automatically.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    Text, Boolean, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """
    Represents an employee/user in the organization.
    Linked to Events, Alerts, and RiskProfiles.
    """
    __tablename__ = "users"

    user_id    = Column(String, primary_key=True, index=True)
    username   = Column(String, nullable=False)
    department = Column(String, nullable=True)
    role       = Column(String, nullable=True)           # e.g. analyst, admin
    email      = Column(String, nullable=True)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships — lets you do user.events to get all events for this user
    events       = relationship("Event",       back_populates="user")
    alerts       = relationship("Alert",       back_populates="user")
    risk_profile = relationship("RiskProfile", back_populates="user", uselist=False)


class Event(Base):
    """
    A single user action/log entry.
    Comes from CSV upload → preprocessed into CTMC states.
    This is what Person 1 reads to run the Markov model.
    """
    __tablename__ = "events"

    event_id    = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String, ForeignKey("users.user_id"), index=True)
    timestamp   = Column(DateTime, nullable=True)
    event_type  = Column(String, nullable=False)   # LOGIN, EMAIL, FILE_ACCESS, etc.
    ctmc_state  = Column(String, nullable=True)    # mapped CTMC state
    activity    = Column(String, nullable=True)    # raw activity field from CSV
    action      = Column(String, nullable=True)    # raw action field from CSV
    description = Column(Text, nullable=True)
    risk_score  = Column(Float, default=0.0)
    rule_count  = Column(Integer, default=0)
    rules_triggered = Column(Text, nullable=True)  # pipe-separated rule names
    is_anomaly  = Column(Boolean, default=False)
    hour        = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    is_after_hours = Column(Boolean, default=False)
    is_weekend  = Column(Boolean, default=False)

    user = relationship("User", back_populates="events")


class NetworkEvent(Base):
    """
    A network-level log entry (DNS, transfers, VPN etc.)
    Comes from network log CSV uploads.
    """
    __tablename__ = "network_events"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String, ForeignKey("users.user_id"), nullable=True)
    timestamp   = Column(DateTime, nullable=True)
    src_ip      = Column(String, nullable=True)
    dst_ip      = Column(String, nullable=True)
    bytes_sent  = Column(Integer, nullable=True)
    protocol    = Column(String, nullable=True)
    event_type  = Column(String, nullable=True)   # DNS, VPN, HTTP, etc.
    is_anomaly  = Column(Boolean, default=False)

    user = relationship("User")


class Alert(Base):
    """
    Generated when an anomaly is detected.
    Person 1 POSTs risk results → backend creates alerts here.
    Person 3 reads from here for the SOC dashboard.
    """
    __tablename__ = "alerts"

    alert_id   = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(String, ForeignKey("users.user_id"), index=True)
    risk_score = Column(Float, nullable=False)
    severity   = Column(String, nullable=False)   # Low / Medium / High / Critical
    status     = Column(String, default="open")   # open / reviewed / closed
    rules_triggered = Column(Text, nullable=True)
    ctmc_log_prob   = Column(Float, nullable=True)
    explanation     = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="alerts")


class RiskProfile(Base):
    """
    Aggregated risk profile per user — updated every time Person 1 sends results.
    Person 3 uses this to show per-user risk on the dashboard.
    """
    __tablename__ = "risk_profiles"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(String, ForeignKey("users.user_id"), unique=True, index=True)
    latest_risk_score = Column(Float, default=0.0)
    max_risk_score    = Column(Float, default=0.0)
    mean_risk_score   = Column(Float, default=0.0)
    severity          = Column(String, default="Low")
    total_alerts      = Column(Integer, default=0)
    open_alerts       = Column(Integer, default=0)
    total_events      = Column(Integer, default=0)
    anomaly_events    = Column(Integer, default=0)
    last_seen         = Column(DateTime, nullable=True)
    updated_at        = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="risk_profile")

class PersonalBehaviorProfile(Base):
    """
    V2.1: Advanced persistent behavioral profile tracking rigid temporal statistics 
    without holding massive raw observation sequences in memory.
    """
    __tablename__ = "personal_behavior_profiles"

    id                       = Column(Integer, primary_key=True, autoincrement=True)
    user_id                  = Column(String, ForeignKey("users.user_id"), unique=True, index=True)
    profile_version          = Column(Integer, default=1)
    session_count            = Column(Integer, default=0)
    first_seen               = Column(DateTime, server_default=func.now())
    last_seen                = Column(DateTime, server_default=func.now(), onupdate=func.now())
    statistics_json          = Column(Text, nullable=True) # Serialized statistical distributions (mean, std, max, percentiles)
    state_distribution_json  = Column(Text, nullable=True) # Normalized probabilities of CTMC state activations
    action_distribution_json = Column(Text, nullable=True) # Normalized probabilities of action triggers
    confidence               = Column(Float, default=0.0)  # Profile confidence derived via LEARNING maturity
    updated_at               = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User")

class AttackChain(Base):
    """
    V2.1: Temporal sequences of attack stages bounded by user and time windows.
    """
    __tablename__ = "attack_chains"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    chain_id       = Column(String, unique=True, index=True)
    user_id        = Column(String, ForeignKey("users.user_id"), index=True)
    first_seen     = Column(DateTime)
    last_seen      = Column(DateTime)
    current_stage  = Column(String)
    stages_json    = Column(Text) # JSON list
    sessions_json  = Column(Text) # JSON list 
    risk_score     = Column(Float, default=0.0)
    confidence     = Column(Float, default=0.0)
    status         = Column(String, default="OPEN") # OPEN, CLOSED
    created_at     = Column(DateTime, server_default=func.now())

    user = relationship("User")

class InvestigationCase(Base):
    """
    V2.1: Analyzed correlation of clustered alerts structurally grouped for SOC analysts.
    """
    __tablename__ = "investigation_cases"

    case_id        = Column(String, primary_key=True, index=True)
    user_id        = Column(String, ForeignKey("users.user_id"), index=True)
    status         = Column(String, default="OPEN") # OPEN, INVESTIGATING, RESOLVED
    risk_score     = Column(Float, default=0.0)
    severity       = Column(String, default="Low")
    current_stage  = Column(String)
    summary        = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    alerts = relationship("CaseAlert", back_populates="case")

class CaseAlert(Base):
    """
    V2.1: Join table binding individual independent alerts into correlated Cases.
    """
    __tablename__ = "case_alerts"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    case_id    = Column(String, ForeignKey("investigation_cases.case_id"))
    alert_id   = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    
    case = relationship("InvestigationCase", back_populates="alerts")