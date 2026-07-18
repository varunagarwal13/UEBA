import sys
import os
import math
import json
from collections import defaultdict, Counter
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app import crud, models, schemas

# Add repository root to sys.path to import analytics package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

try:
    from analytics.pipeline.analytics_pipeline import AnalyticsPipeline
    from analytics.ctmc.population_matrix import load_population_matrix
    from analytics.data.spedia.loader import load_spedia_sessions
except ImportError as e:
    print(f"Error importing analytics modules: {e}")

router = APIRouter(prefix="/simulator", tags=["Pipeline Simulator"])


class SimulationState:
    def __init__(self):
        self.pipeline: Optional[AnalyticsPipeline] = None
        self.test_sessions: List[Dict[str, Any]] = []
        self.current_index = 0
        self.stats = {
            "tp": 0, "fp": 0, "tn": 0, "fn": 0,
            "alerts_generated": 0,
            "processed": 0
        }
        self.auto_run = False
        self.initialized = False


# Global simulator state
sim_state = SimulationState()


def init_simulator_state(db: Session):
    """
    Initializes the simulator:
    1. Loads the ctmc transition matrix.
    2. Loads SPEDIA sessions.
    3. Splits sessions 80/20.
    4. Trains the pipeline on the 80% train split.
    5. Seeds the SQLite database with training events if it is empty.
    """
    if sim_state.initialized:
        return

    print("[SIMULATOR] Starting initialization...")

    # Load baseline population matrix
    matrix_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "..", 
        "spedia_anomaly_detection", "data", "ctmc_transition_matrix.csv"
    ))
    population_matrix = load_population_matrix(matrix_path)
    sim_state.pipeline = AnalyticsPipeline(population_matrix)

    # Load flat SPEDIA logs and compile sessions
    csv_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "SPEDIA_preprocessed.csv"
    ))
    sessions = load_spedia_sessions(csv_path)

    # Group sessions by user to preserve temporal profiles per user
    user_sessions = defaultdict(list)
    for s in sessions:
        user_sessions[s["user_id"]].append(s)

    train_sessions = []
    test_sessions = []

    for user, u_sessions in user_sessions.items():
        split = max(1, int(len(u_sessions) * 0.8))

        # Build personal user profile transition matrix
        counts = defaultdict(Counter)
        for session in u_sessions[:split]:
            train_sessions.append(session)
            sts = [e.get("CTMC_State", "") for e in session["events"] if e.get("CTMC_State")]
            for i in range(len(sts) - 1):
                counts[sts[i]][sts[i+1]] += 1

        matrix = {}
        for from_s, to_counts in counts.items():
            tot = sum(to_counts.values())
            matrix[from_s] = {t: c/tot for t, c in to_counts.items()}

        if matrix:
            sim_state.pipeline.user_matrices[user] = matrix
            sim_state.pipeline.user_session_counts[user] = split

        test_sessions.extend(u_sessions[split:])

    sim_state.test_sessions = test_sessions
    sim_state.current_index = 0
    sim_state.stats = {
        "tp": 0, "fp": 0, "tn": 0, "fn": 0,
        "alerts_generated": 0,
        "processed": 0
    }

    # Seed training events into database if empty
    has_events = db.query(models.Event).first() is not None
    if not has_events:
        print(f"[SIMULATOR] Seeding database with {len(train_sessions)} training sessions...")
        # Get all unique users
        unique_users = set(s["user_id"] for s in train_sessions)
        for uid in unique_users:
            crud.get_or_create_user(db, uid)

        records = []
        for s in train_sessions:
            for e in s["events"]:
                ts_str = e.get("timestamp")
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else None
                hour = ts.hour if ts else None
                dow = ts.weekday() if ts else None

                rules_triggered = []
                for col in e.keys():
                    if col.startswith("Rule_") and e[col] == 1:
                        # Convert Rule_R01 to R01
                        rules_triggered.append(col.replace("Rule_", ""))

                records.append({
                    "user_id": e.get("user_id"),
                    "timestamp": ts,
                    "event_type": e.get("Activity", "").upper(),
                    "ctmc_state": e.get("CTMC_State"),
                    "activity": e.get("Activity"),
                    "action": e.get("Action"),
                    "description": e.get("Command") or e.get("file_path") or "",
                    "risk_score": float(e.get("Level", 0.0)),
                    "rule_count": len(rules_triggered),
                    "rules_triggered": "|".join(rules_triggered),
                    "is_anomaly": bool(e.get("Anomaly", 0) == 1),
                    "hour": hour,
                    "day_of_week": dow,
                    "is_after_hours": bool(hour is not None and (hour < 7 or hour > 20)),
                    "is_weekend": bool(dow is not None and dow >= 5),
                })

        # Bulk insert
        CHUNK = 5000
        for i in range(0, len(records), CHUNK):
            crud.bulk_insert_events(db, records[i:i+CHUNK])
        print(f"[SIMULATOR] Seeded {len(records)} events successfully.")

    sim_state.initialized = True
    print("[SIMULATOR] Initialization complete.")


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    """Returns the current simulation statistics and state."""
    # Ensure simulator is initialized
    init_simulator_state(db)

    tp, fp, tn, fn = sim_state.stats["tp"], sim_state.stats["fp"], sim_state.stats["tn"], sim_state.stats["fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "initialized": sim_state.initialized,
        "processed": sim_state.stats["processed"],
        "total_test_sessions": len(sim_state.test_sessions),
        "current_index": sim_state.current_index,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1_score": round(f1, 2),
        "alerts_generated": sim_state.stats["alerts_generated"],
        "auto_run": sim_state.auto_run
    }


@router.post("/step")
def step_simulation(db: Session = Depends(get_db)):
    """Processes the next test session through the analytics pipeline and returns the full trace."""
    init_simulator_state(db)

    if sim_state.current_index >= len(sim_state.test_sessions):
        return {
            "status": "completed",
            "message": "All test sessions have been processed."
        }

    session = sim_state.test_sessions[sim_state.current_index]
    sim_state.current_index += 1
    sim_state.stats["processed"] += 1

    user_id = session["user_id"]
    session_id = session["session_id"]
    anomaly_gt = session.get("anomaly", 0)

    # 1. State Extraction Stage
    states = sim_state.pipeline.state_extractor.extract_states(session)

    # 2. CTMC Probability Engine Stage
    matrix = sim_state.pipeline.user_matrices.get(user_id, sim_state.pipeline.population_matrix)
    total_sessions = sim_state.pipeline.user_session_counts.get(user_id, 0)
    ctmc_score = sim_state.pipeline.ctmc_scorer.score(states, matrix, total_sessions)

    # 3. Rule Engine Stage
    violations = sim_state.pipeline.rule_engine.check_all_rules(
        states, session.get("events", []), user_id=user_id
    )
    rule_score = min(100.0, sum(v.score_contribution for v in violations))

    # 4. Risk Fusion Stage
    risk_res = sim_state.pipeline.risk_scorer.compute(
        user_id=user_id, session_id=session_id,
        ctmc_score=ctmc_score, violations=violations,
        total_sessions=total_sessions
    )

    alert_triggered = bool(risk_res.risk_score >= 5.0)
    alert_created = None
    alert_id_assigned = ""

    # 5. Explainability Stage (Always run to display real trace data on dashboard)
    temp_alert_id = f"TEMP-{session_id}"
    explanation = sim_state.pipeline.explainer.explain(
        alert_id=temp_alert_id,
        user_id=user_id,
        state_sequence=states,
        violations=violations,
        risk_score=risk_res.risk_score,
        severity=risk_res.severity,
        ctmc_score=ctmc_score,
        rule_score=rule_score,
        confidence=risk_res.confidence
    )

    # 6. Alert Generation & Database Storage Stage
    if alert_triggered:
        sim_state.stats["alerts_generated"] += 1
        if anomaly_gt == 1:
            sim_state.stats["tp"] += 1
        else:
            sim_state.stats["fp"] += 1

        import uuid
        real_alert_id = f"ALT{str(uuid.uuid4())[:8].upper()}"
        alert_id_assigned = real_alert_id

        # Update explanation object with real alert ID
        explanation.alert_id = real_alert_id

        # Compile full pipeline result structure
        pipeline_result = {
            "alert": {
                "alert_id": real_alert_id,
                "user_id": user_id,
                "risk_score": risk_res.risk_score,
                "severity": risk_res.severity,
                "detection_type": "CTMC+RULES",
                "confidence": risk_res.confidence,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
            "explanation": {
                "alert_id": real_alert_id,
                "summary": explanation.summary,
                "reasons": explanation.reasons,
                "recommended_actions": explanation.recommended_actions,
                "risk_context": explanation.risk_context,
                "detection_methods": explanation.detection_methods,
            },
            "model_breakdown": {
                "ctmc_score": ctmc_score,
                "rule_score": rule_score,
                "if_score": 0.0,
                "rule_violations": [
                    {"rule_id": v.rule_id, "rule_name": v.rule_name, "severity": v.severity}
                    for v in violations
                ]
            },
            "timeline": {
                "user_id": user_id,
                "timeline": explanation.timeline,
                "timeline_compact": explanation.timeline_compact,
            },
            "ground_truth": anomaly_gt
        }

        # Store alert in DB
        rules_triggered_str = "|".join(v.rule_id for v in violations)
        payload = schemas.AnalyticsResult(
            user_id = user_id,
            risk_score = risk_res.risk_score,
            severity = risk_res.severity,
            rules_triggered = rules_triggered_str,
            ctmc_log_prob = ctmc_score,
            explanation = json.dumps(pipeline_result)
        )
        
        alert_orm = crud.store_analytics_result(db, payload)
        alert_created = {
            "alert_id": alert_orm.alert_id,
            "risk_score": alert_orm.risk_score,
            "severity": alert_orm.severity,
            "rules_triggered": alert_orm.rules_triggered,
            "explanation": pipeline_result
        }
    else:
        if anomaly_gt == 1:
            sim_state.stats["fn"] += 1
        else:
            sim_state.stats["tn"] += 1

    # Save session events to SQLite DB
    records = []
    for e in session["events"]:
        ts_str = e.get("timestamp")
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else None
        hour = ts.hour if ts else None
        dow = ts.weekday() if ts else None

        rules_triggered = []
        for col in e.keys():
            if col.startswith("Rule_") and e[col] == 1:
                rules_triggered.append(col.replace("Rule_", ""))

        records.append({
            "user_id": e.get("user_id"),
            "timestamp": ts,
            "event_type": e.get("Activity", "").upper(),
            "ctmc_state": e.get("CTMC_State"),
            "activity": e.get("Activity"),
            "action": e.get("Action"),
            "description": e.get("Command") or e.get("file_path") or "",
            "risk_score": float(e.get("Level", 0.0)),
            "rule_count": len(rules_triggered),
            "rules_triggered": "|".join(rules_triggered),
            "is_anomaly": bool(anomaly_gt == 1),
            "hour": hour,
            "day_of_week": dow,
            "is_after_hours": bool(hour is not None and (hour < 7 or hour > 20)),
            "is_weekend": bool(dow is not None and dow >= 5),
        })

    crud.bulk_insert_events(db, records)

    # Return comprehensive trace representing the full data flow
    return {
        "status": "processed",
        "session_id": session_id,
        "user_id": user_id,
        "ground_truth": anomaly_gt,
        "event_count": len(session["events"]),
        "alert_triggered": alert_triggered,
        "pipeline_trace": {
            "session_id": session_id,
            "event_count": len(session["events"]),
            "states": states,
            "ctmc_score": round(ctmc_score, 1),
            "rules_checked": 13,
            "rule_score": round(rule_score, 1),
            "rule_violations": [
                {"rule_id": v.rule_id, "rule_name": v.rule_name, "severity": v.severity}
                for v in violations
            ],
            "final_risk_score": round(risk_res.risk_score, 1),
            "severity": risk_res.severity,
            "confidence": round(risk_res.confidence, 2),
            "alert_id": alert_created["alert_id"] if alert_created else None,
            "explanation": {
                "summary": explanation.summary,
                "reasons": explanation.reasons,
                "recommended_actions": explanation.recommended_actions,
                "risk_context": explanation.risk_context,
                "detection_methods": explanation.detection_methods,
            },
            "timeline": {
                "timeline": explanation.timeline,
                "timeline_compact": explanation.timeline_compact,
            }
        }
    }



@router.post("/reset")
def reset_simulation(db: Session = Depends(get_db)):
    """Resets the simulator stats, clear alerts, and clear simulated events from the DB."""
    # Ensure initialized
    init_simulator_state(db)

    sim_state.current_index = 0
    sim_state.stats = {
        "tp": 0, "fp": 0, "tn": 0, "fn": 0,
        "alerts_generated": 0,
        "processed": 0
    }
    sim_state.auto_run = False

    # Clear SQLite alerts and simulated events
    # Training events are kept, simulated events are deleted
    # We identify simulated events because we know total train sessions. 
    # But a cleaner way is: delete all alerts, all risk profiles, and delete all events 
    # then re-seed training data, or simply delete alerts and risk profiles.
    # To be extremely clean, we will:
    # 1. Truncate alerts, risk profiles, events, users.
    # 2. Re-initialize and re-seed.
    print("[SIMULATOR] Resetting database...")
    db.query(models.Alert).delete()
    db.query(models.RiskProfile).delete()
    db.query(models.Event).delete()
    db.query(models.User).delete()
    db.commit()

    sim_state.initialized = False
    init_simulator_state(db)

    return {
        "status": "reset",
        "message": "Simulation stats, alerts, and DB have been reset."
    }


@router.post("/auto-run/toggle")
def toggle_auto_run(db: Session = Depends(get_db)):
    """Toggles simulator auto-run status."""
    sim_state.auto_run = not sim_state.auto_run
    return {
        "auto_run": sim_state.auto_run
    }
