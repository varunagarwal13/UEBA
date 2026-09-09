import os
import sys
import copy

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from analytics.pipeline.analytics_pipeline import AnalyticsPipeline
from datetime import datetime

# Phase 16: Determinism Constraints
def test_pipeline_determinism():
    pipeline = AnalyticsPipeline(population_matrix={})
    pipeline.ALERT_THRESHOLD = -100.0
    
    mock_session = {
        "user_id": "det_user_1",
        "session_id": "sess-alpha",
        "start_time": datetime(2025, 3, 26, 12, 0, 0),
        "events": [
            {"event_type": "Login"},
            {"event_type": "File_Access", "action": "chmod -r 777"},
            {"event_type": "Command", "action": "whoami"},
            {"event_type": "Command", "action": "netstat"}
        ]
    }
    
    # Run 1
    res1 = pipeline.process_session(copy.deepcopy(mock_session))
    
    # Run 2 on same object
    res2 = pipeline.process_session(copy.deepcopy(mock_session))
    
    assert res1 is not None and res2 is not None
    assert res1["alert"]["risk_score"] == res2["alert"]["risk_score"], "Risk fusion is non-deterministic!"
    assert res1["investigation_case"]["case_id"] == res2["investigation_case"]["case_id"], "Case correlation broke determinism!"
    assert res1["alert"]["attack_stage"] == res2["alert"]["attack_stage"], "Attack chain broke determinism!"
