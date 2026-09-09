import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from analytics.pipeline.analytics_pipeline import AnalyticsPipeline
from datetime import datetime

# Phase 15: Failure Injection
def test_failure_injection_missing_telemetry():
    pipeline = AnalyticsPipeline(population_matrix={})
    pipeline.ALERT_THRESHOLD = -100.0
    
    # Force Missing IF
    pipeline.if_model = None 
    
    # Highly anomalous base session bypassing IF via rules / actions
    mock_session = {
        "user_id": "fail_inj_user1",
        "session_id": "sess-beta",
        "start_time": datetime(2025, 3, 26, 12, 0, 0),
        "events": [
            {"event_type": "Login", "is_anomaly": True},
            {"event_type": "File_Access", "action": "mass file exfil"},
            {"event_type": "File_Access", "action": "sudo"}
        ]
    }
    
    res = pipeline.process_session(mock_session)
    assert res is not None, "Pipeline crashed rather than degrading gracefully on missing IF model!"
    
    # Ensure explicit Unavailable checks
    assert "UNAVAILABLE" in res["explanation"]["risk_context"].upper(), "Risk context hallucinated IF output when it was forcibly disabled!"
    assert res["alert"]["confidence"] < 0.90, "Confidence did not penalize properly upon IF Failure injection."
