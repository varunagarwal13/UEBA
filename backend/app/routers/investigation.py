"""
routers/investigation.py
------------------------
Read-only V2.1 endpoints: attack chains, investigation cases and
personal behaviour profiles. Populated by the analytics pipeline on
POST /logs/user.
"""

import json
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas
from typing import List, Optional

router = APIRouter(tags=["Investigation"])


@router.get("/attack-chains", response_model=List[schemas.AttackChainOut])
def get_attack_chains(
    status: Optional[str] = Query(None, description="Filter by: OPEN/CLOSED"),
    limit:  int           = Query(100),
    db: Session = Depends(get_db)
):
    chains = []
    for c in crud.get_attack_chains(db, status=status, limit=limit):
        sessions = json.loads(c.sessions_json or "[]")
        chains.append({
            "chain_id":      c.chain_id,
            "user_id":       c.user_id,
            "first_seen":    c.first_seen,
            "last_seen":     c.last_seen,
            "current_stage": c.current_stage,
            # older rows hold bare stage names; newer ones carry session/time/evidence
            "stages":        [s if isinstance(s, dict) else {"stage": s} for s in json.loads(c.stages_json or "[]")],
            "sessions":      sessions,
            "risk_score":    c.risk_score or 0.0,
            "confidence":    c.confidence or 0.0,
            "status":        c.status,
        })
    return chains


@router.get("/cases", response_model=List[schemas.CaseOut])
def get_cases(
    status: Optional[str] = Query(None, description="Filter by: OPEN/INVESTIGATING/RESOLVED"),
    limit:  int           = Query(100),
    db: Session = Depends(get_db)
):
    # link each case to the user's chain whose time window overlaps the case's
    chains_by_user = {}
    for ch in crud.get_attack_chains(db, limit=5000):
        chains_by_user.setdefault(ch.user_id, []).append(ch)

    def chain_for(c):
        for ch in chains_by_user.get(c.user_id, []):
            if ch.first_seen and ch.last_seen and c.created_at and c.updated_at \
                    and ch.first_seen <= c.updated_at and c.created_at <= ch.last_seen:
                return ch.chain_id
        return None

    return [{
        "case_id":       c.case_id,
        "user_id":       c.user_id,
        "status":        c.status,
        "risk_score":    c.risk_score or 0.0,
        "severity":      c.severity,
        "current_stage": c.current_stage,
        "summary":       c.summary,
        "alert_ids":     [int(a.alert_id) for a in c.alerts if str(a.alert_id).isdigit()],
        "chain_id":      chain_for(c),
        "created_at":    c.created_at,
        "updated_at":    c.updated_at,
    } for c in crud.get_cases(db, status=status, limit=limit)]


@router.get("/profiles/{user_id}", response_model=schemas.BehaviorProfileOut)
def get_profile(user_id: str, db: Session = Depends(get_db)):
    pb = crud.get_behavior_profile(db, user_id)
    if not pb:
        raise HTTPException(404, f"No behaviour profile for {user_id}.")

    stats = {}
    for name, s in json.loads(pb.statistics_json or "{}").items():
        n = s.get("count", 0)
        std = math.sqrt(s.get("variance", 0.0) / (n - 1)) if n > 1 else 0.0
        stats[name] = {"mean": s.get("mean", 0.0), "std": std, "current": s.get("max_val", 0.0),
                       "min": s.get("min_val", 0.0), "count": n}

    # profile_builder never fills state_distribution, so derive it from ingested events
    dist = json.loads(pb.state_distribution_json or "{}") or crud.get_state_distribution(db, user_id)

    return {
        "user_id":            user_id,
        "profile_version":    pb.profile_version or 1,
        "session_count":      pb.session_count or 0,
        "confidence":         pb.confidence or 0.0,
        "state_distribution": dist,
        "statistics":         stats,
        "hourly":             crud.get_hourly_activity(db, user_id),
    }
