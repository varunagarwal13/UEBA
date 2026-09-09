from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import uuid
from analytics.attack_chain.attack_stage import AttackStage, get_stage_severity

class AttackChainState:
    def __init__(self, user_id: str, chain_id: Optional[str] = None):
        self.chain_id = chain_id or f"CHN-{str(uuid.uuid4())[:8].upper()}"
        self.user_id = user_id
        self.first_seen: datetime = datetime.utcnow()
        self.last_seen: datetime = datetime.utcnow()
        
        # ordered list of specific stages hit
        self.stages_hit: List[str] = []
        self.current_stage: str = AttackStage.UNKNOWN.value
        
        self.risk_score: float = 0.0
        self.confidence: float = 0.0
        self.status: str = "OPEN" # OPEN, CLOSED
        
        # internal marker to hold session linkages
        self.related_sessions: List[str] = []

class AttackChainEngine:
    def __init__(self, temporal_window_hours: int = 24):
        self.temporal_window = timedelta(hours=temporal_window_hours)
        
    def _calculate_score(self, chain: AttackChainState) -> float:
        """
        Bounded 0-100 logic evaluating progression maturity.
        Do not just sum up scores blindly; bound the progression mathematically.
        """
        stages = [AttackStage(s) for s in chain.stages_hit]
        
        unique_stages = len(set(stages))
        max_severity = max([get_stage_severity(s) for s in stages]) if stages else 0
        
        base_score = 10.0 * unique_stages
        severity_mult = max_severity * 5.0
        
        # High multi-stage progression jumps scores dramatically
        progression_multiplier = 1.0
        if unique_stages >= 3:
            progression_multiplier = 1.5
        if unique_stages >= 5:
            progression_multiplier = 2.0
            
        raw = (base_score + severity_mult) * progression_multiplier
        return min(raw, 100.0)
        
    def process_event(self, active_chain: Optional[AttackChainState], user_id: str, session_id: str, stage: AttackStage, timestamp: datetime) -> AttackChainState:
        """
        Strict causality boundary constraints (Phase 3 Requirement).
        Only processes chronologically received events against temporal windows.
        """
        if active_chain is None:
            active_chain = AttackChainState(user_id=user_id)
            active_chain.first_seen = timestamp
            
        # Is the chain temporally broken?
        if timestamp - active_chain.last_seen > self.temporal_window:
            active_chain.status = "CLOSED"
            # Return a strictly new chain because timescale snapped
            new_chain = AttackChainState(user_id=user_id)
            new_chain.first_seen = timestamp
            active_chain = new_chain
            
        active_chain.last_seen = timestamp
        
        if stage != AttackStage.UNKNOWN:
            if not active_chain.stages_hit or active_chain.stages_hit[-1] != stage.value:
                active_chain.stages_hit.append(stage.value)
                active_chain.current_stage = stage.value
                
        active_chain.related_sessions.append(session_id)
        active_chain.risk_score = self._calculate_score(active_chain)
        
        # Bounding confidence
        active_chain.confidence = min(0.2 + (len(active_chain.stages_hit) * 0.15), 1.0)
        
        return active_chain
