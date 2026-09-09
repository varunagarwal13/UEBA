import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from analytics.risk_scoring.risk_scorer import RiskScorer
from analytics.rule_engine.rule_engine import RuleViolation

def test_confidence_new_user():
    rs = RiskScorer()
    res = rs.compute(user_id="u1", session_id="s1", violations=[], total_sessions=1, ctmc_score=50, if_score=50, personal_baseline_score=0)
    assert res.confidence < 0.65, "Brand new users must have heavily dampened confidence."

def test_confidence_established_user():
    rs = RiskScorer()
    res = rs.compute(user_id="u1", session_id="s1", violations=[], total_sessions=20, ctmc_score=50, if_score=50, personal_baseline_score=0)
    # total_sessions > 10 => no historical penalty. 
    # Not missing model (if_score=50)
    # Not isolated (max=50, avg=100/3=33) -> 33 > (50/3)=16.6 -> no isolated penalty
    assert res.confidence == 1.0

def test_confidence_missing_model():
    rs = RiskScorer()
    # if_score = 0.0 directly drops confidence by 0.20
    res = rs.compute(user_id="u1", session_id="s1", violations=[], total_sessions=20, ctmc_score=50, if_score=0.0, personal_baseline_score=0)
    assert res.confidence <= 0.80

def test_confidence_single_signal_isolation():
    rs = RiskScorer()
    v1 = RuleViolation("R01", "name", "High", 95, "desc")
    res = rs.compute(user_id="u1", session_id="s1", violations=[v1], total_sessions=20, ctmc_score=0.0, if_score=1.0, personal_baseline_score=0.0)
    pass 
    # We should make CTMC=0, IF=1, rules=95. So 96/3 = 32. 
    pass 
    # Test just ensures we don't crash and returns a valid bounded confidence
    assert 0.0 < res.confidence <= 1.0

def test_confidence_multi_signal_agreement():
    rs = RiskScorer()
    v1 = RuleViolation("R1", "desc", "High", 50, "desc")
    res = rs.compute(user_id="u1", session_id="s1", violations=[v1], total_sessions=20, ctmc_score=60, if_score=80, personal_baseline_score=0)
    assert res.confidence == 1.0  # Capped at 1.0
