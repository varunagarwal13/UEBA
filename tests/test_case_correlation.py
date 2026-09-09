import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from datetime import datetime, timedelta
from analytics.cases.case_engine import CaseEngine

def test_case_correlation():
    engine = CaseEngine(time_window_hours=24)
    t1 = datetime(2025, 3, 10, 12, 0, 0)
    
    # 1. First alert creates new case
    case = engine.evaluate_alert("u1", "ALT-1", 70.0, "RECONNAISSANCE", t1, [])
    
    assert case["case_id"].startswith("CAS-")
    assert len(case["alerts"]) == 1
    assert case["risk_score"] == 70.0
    
    # 2. Second alert 5 minutes later links identically
    open_cases = [case]
    case_updated = engine.evaluate_alert("u1", "ALT-2", 80.0, "COLLECTION", t1 + timedelta(minutes=5), open_cases)
    
    # Verify exact same object was returned
    assert case_updated["case_id"] == case["case_id"]
    assert len(case_updated["alerts"]) == 2
    assert case_updated["current_stage"] == "COLLECTION"
    assert case_updated["risk_score"] == 70.0 + (80.0 * 0.2)
    assert "2 correlated alerts" in case_updated["summary"]
    
    # 3. Third alert 48 hours later (out of bounds) -> creates completely new case
    case_new = engine.evaluate_alert("u1", "ALT-3", 55.0, "EXFILTRATION", t1 + timedelta(hours=48), [case_updated])
    
    assert case_new["case_id"] != case_updated["case_id"]
    assert len(case_new["alerts"]) == 1
    assert case_new["risk_score"] == 55.0
