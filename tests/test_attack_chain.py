import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from datetime import datetime, timedelta
from analytics.attack_chain.attack_stage import AttackStage
from analytics.attack_chain.attack_chain_engine import AttackChainEngine, AttackChainState

def test_attack_chain_causality():
    # Enforces explicit chronological isolation bounds
    engine = AttackChainEngine(temporal_window_hours=24)
    t1 = datetime(2025, 3, 10, 10, 0, 0)
    
    chain = engine.process_event(None, "u1", "sess1", AttackStage.RECONNAISSANCE, t1)
    assert chain.current_stage == "RECONNAISSANCE"
    assert len(chain.stages_hit) == 1
    
    # 25 hours later -> temporal bound failure, chain fractures!
    t2 = t1 + timedelta(hours=25)
    new_chain = engine.process_event(chain, "u1", "sess2", AttackStage.COLLECTION, t2)
    
    assert new_chain.chain_id != chain.chain_id
    assert new_chain.current_stage == "COLLECTION"
    assert len(new_chain.stages_hit) == 1 # Only Collection is present on this isolated chain
    assert chain.status == "CLOSED"

def test_score_progression():
    engine = AttackChainEngine(temporal_window_hours=24)
    t1 = datetime(2025, 3, 10, 10, 0, 0)
    
    chain = engine.process_event(None, "u1", "sess1", AttackStage.RECONNAISSANCE, t1)
    s1 = chain.risk_score
    
    chain = engine.process_event(chain, "u1", "sess2", AttackStage.PRIVILEGE_ESCALATION, t1 + timedelta(minutes=5))
    s2 = chain.risk_score
    
    chain = engine.process_event(chain, "u1", "sess3", AttackStage.EXFILTRATION, t1 + timedelta(minutes=10))
    s3 = chain.risk_score
    
    assert s1 < s2 < s3
    assert s3 > 75.0, "Score multiplier must explode accurately bounding deep multi-stage progressions"
