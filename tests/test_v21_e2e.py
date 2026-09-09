import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from analytics.pipeline.analytics_pipeline import AnalyticsPipeline
from datetime import datetime

# Phase 17: Validating E2E
def test_v21_e2e_flow():
    pipeline = AnalyticsPipeline(population_matrix={})
    pipeline.ALERT_THRESHOLD = -100.0
    
    # Emulate real API parsing
    session = {
        "user_id": "e2e_user1",
        "session_id": "sess-omega",
        "start_time": datetime(2025, 3, 28, 12, 0, 0),
        "events": [
            {"event_type": "Login", "action": "LOGIN", "timestamp": datetime(2025, 3, 28, 12, 0, 0)},
            {"event_type": "Command", "action": "whoami", "timestamp": datetime(2025, 3, 28, 12, 5, 0)},
            {"event_type": "Command", "action": "netstat", "timestamp": datetime(2025, 3, 28, 12, 10, 0)},
            {"event_type": "File_Access", "action": "zip", "timestamp": datetime(2025, 3, 28, 12, 15, 0)} # Triggers staging attack bound
        ]
    }
    
    res = pipeline.process_session(session)
    
    assert res is not None
    assert "alert" in res
    assert "investigation_case" in res, "Case correlator failed to map the alert."
    assert "explanation" in res
    
    alert = res["alert"]
    case = res["investigation_case"]
    
    assert alert["attack_stage"] == "STAGING", "Attack stage causality was isolated properly."
    assert "CAS-" in case["case_id"]
    assert alert["alert_id"] in case["alerts"]
    assert "STAGING" in res["explanation"]["recommended_actions"][1], "Explanation decoupled from reality."
