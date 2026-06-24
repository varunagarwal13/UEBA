# Analytics Domain — Backend Integration Guide
# For: Person 2 (Platform & Backend Engineer)
# Written by: Person 1 (Analytics & ML Engineer)

---

## What This Document Covers

This document tells you exactly how to call the analytics pipeline
from your FastAPI/Flask backend. You do not need to understand the
internals — just follow the steps below.

---

## Step 1 — Install Analytics Dependencies

From the repo root:

    pip install -r analytics/requirements.txt

---

## Step 2 — Initialize the Pipeline (Once at Startup)

Do this ONCE when your backend server starts, not on every request.
Creating the pipeline is expensive. Reusing it is cheap.

    from analytics.pipeline.analytics_pipeline import AnalyticsPipeline
    from analytics.ctmc.population_matrix import load_population_matrix

    # Load the population baseline matrix (shipped with the repo)
    population_matrix = load_population_matrix(
        "spedia_anomaly_detection/data/ctmc_transition_matrix.csv"
    )

    # Create the pipeline — do this once at server startup
    pipeline = AnalyticsPipeline(population_matrix)

---

## Step 3 — Load User Profiles (Once at Startup)

The pipeline needs historical sessions to build behavioral profiles.
Load these from your database at startup and pass them to the pipeline.

    from collections import defaultdict, Counter

    def build_user_matrix(historical_sessions):
        counts = defaultdict(Counter)
        for session in historical_sessions:
            states = [
                e.get("CTMC_State", "") or e.get("event_type", "")
                for e in session.get("events", [])
                if e.get("CTMC_State") or e.get("event_type")
            ]
            for i in range(len(states) - 1):
                counts[states[i]][states[i+1]] += 1
        matrix = {}
        for from_s, to_counts in counts.items():
            total = sum(to_counts.values())
            matrix[from_s] = {t: c/total for t, c in to_counts.items()}
        return matrix

    # For each user in your database, load their historical sessions
    # and build a personal transition matrix
    for user_id, user_sessions in historical_sessions_by_user.items():
        matrix = build_user_matrix(user_sessions)
        if matrix:
            pipeline.user_matrices[user_id]       = matrix
            pipeline.user_session_counts[user_id] = len(user_sessions)

---

## Step 4 — Call the Pipeline for Each New Session

Call this every time a new session is ready (after sessionization).

    result = pipeline.process_session(session_dict)

    if result is None:
        # Session is normal — no alert generated — do nothing
        pass
    else:
        # Alert generated — store in your database
        store_alert(result)

---

## Input Format (What You Send)

Every session dict must match this exact format:

    {
        "session_id": "S001",           # string, your unique session ID
        "user_id":    "john.doe",       # string, the username
        "events": [                     # list of event dicts, in time order
            {
                "event_id":     "EV001",
                "user_id":      "john.doe",
                "timestamp":    "2026-06-25T09:15:00Z",  # ISO 8601 UTC
                "Activity":     "session",               # REQUIRED for state extraction
                "Action":       "Login",                 # REQUIRED
                "Level":        3.0,                     # Wazuh alert level (float)
                "Command":      "",                      # command string or ""
                "file_path":    "",                      # file path or ""
                "Filename":     "",                      # filename or ""
                "bytes":        0.0,                     # transfer size
                "IsAfterHours": 0,                       # 1 if outside 8am-8pm
                "IsWeekend":    0,                       # 1 if Saturday or Sunday
                "CTMC_State":   "Login",                 # pre-computed state (optional)
                "Anomaly":      0                        # ground truth (optional)
            }
        ]
    }

### CRITICAL FIELDS

These two fields drive state extraction.
If they are missing or empty, events will be skipped:

    Activity  — must be one of:
                "session", "command", "file", "email",
                "browser", "network", "device"

    Action    — the specific action string from your log parser

### OPTIONAL: CTMC_State

If you pre-compute the CTMC_State in your ingestion pipeline
(e.g. by reading it from SPEDIA_preprocessed.csv), include it.
The state extractor will use it directly and skip its own logic.
This is faster and more accurate.

If CTMC_State is empty or missing, the extractor will derive
the state from Activity + Action + Level + Command.

### IsAfterHours and IsWeekend

Compute these in your ingestion pipeline:

    from datetime import datetime

    def compute_time_features(timestamp_str):
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        hour       = dt.hour
        day        = dt.weekday()   # 0=Monday, 6=Sunday
        is_after   = 1 if (hour >= 22 or hour < 6) else 0
        is_weekend = 1 if day >= 5 else 0
        return is_after, is_weekend

---

## Output Format (What You Receive)

When result is not None, it is a dict with this structure:

    {
        "alert": {
            "alert_id":       "ALT685520E4",   # unique alert ID
            "user_id":        "john.doe",
            "risk_score":     92.0,            # float 0-100
            "severity":       "Critical",      # Low/Medium/High/Critical
            "detection_type": "CTMC+RULES",
            "confidence":     0.95,            # float 0.0-1.0
            "timestamp":      "2026-06-25T09:23:00Z"
        },
        "explanation": {
            "alert_id":   "ALT685520E4",
            "summary":    "User john.doe logged in outside working hours...",
            "reasons":    [
                "Login occurred outside normal working hours...",
                "File access was followed by file creation or upload..."
            ],
            "recommended_actions": [
                "Immediately review the full session event log...",
                "Consider temporarily suspending the user account..."
            ],
            "risk_context":      "Risk score 92/100 (Critical)...",
            "detection_methods": ["Behavioral model (CTMC): score 85/100...", "..."]
        },
        "model_breakdown": {
            "ctmc_score": 85.2,
            "rule_score": 100.0,
            "if_score":   0.0,
            "rule_violations": [
                {
                    "rule_id":   "R01",
                    "rule_name": "After-hours login",
                    "severity":  "Medium"
                }
            ]
        },
        "timeline": {
            "user_id":          "john.doe",
            "timeline":         ["User logged in successfully", "..."],
            "timeline_compact": ["User logged in successfully (x2)", "..."]
        }
    }

---

## Database Schema (Suggested Tables)

Store these fields from the output:

### alerts table

    alert_id        VARCHAR PRIMARY KEY
    user_id         VARCHAR NOT NULL
    session_id      VARCHAR
    risk_score      FLOAT
    severity        VARCHAR        -- Low/Medium/High/Critical
    detection_type  VARCHAR
    confidence      FLOAT
    timestamp       TIMESTAMP
    created_at      TIMESTAMP DEFAULT NOW()

### alert_explanations table

    alert_id              VARCHAR PRIMARY KEY REFERENCES alerts(alert_id)
    summary               TEXT
    reasons               JSONB   -- list of strings
    recommended_actions   JSONB   -- list of strings
    risk_context          TEXT
    detection_methods     JSONB   -- list of strings

### alert_model_breakdown table

    alert_id          VARCHAR PRIMARY KEY REFERENCES alerts(alert_id)
    ctmc_score        FLOAT
    rule_score        FLOAT
    if_score          FLOAT
    rule_violations   JSONB   -- list of {rule_id, rule_name, severity}

### alert_timelines table

    alert_id          VARCHAR PRIMARY KEY REFERENCES alerts(alert_id)
    user_id           VARCHAR
    timeline          JSONB   -- full list of strings
    timeline_compact  JSONB   -- deduplicated list

---

## FastAPI Integration Example

Here is a minimal working example for your backend:

    from fastapi import FastAPI
    from analytics.pipeline.analytics_pipeline import AnalyticsPipeline
    from analytics.ctmc.population_matrix import load_population_matrix

    app = FastAPI()

    # Initialize once at startup
    @app.on_event("startup")
    async def startup():
        global pipeline
        population_matrix = load_population_matrix(
            "spedia_anomaly_detection/data/ctmc_transition_matrix.csv"
        )
        pipeline = AnalyticsPipeline(population_matrix)
        # TODO: load historical user profiles from your database here

    # Call this endpoint when a session is ready
    @app.post("/api/analytics/process-session")
    async def process_session(session: dict):
        result = pipeline.process_session(session)
        if result is None:
            return {"status": "normal", "alert": None}
        return {"status": "alert", "alert": result}

---

## Error Handling

The pipeline never raises exceptions for bad input — it returns None.
The following inputs all safely return None:

    - Empty events list
    - Sessions with fewer than 3 events
    - Unknown user (uses population matrix as fallback)
    - Missing Activity or Action fields (events are skipped)
    - Malformed timestamps (treated as not-after-hours)

You do not need try/except around process_session() calls.

---

## Questions

Contact Person 1 for any questions about:
- Input field format
- State extraction logic
- Why a specific alert fired
- Adding new detection rules

Do NOT modify any files inside analytics/ directly.
All changes to detection logic go through Person 1.
