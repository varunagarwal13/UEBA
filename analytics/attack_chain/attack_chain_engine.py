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

        # one entry per stages_hit item: {stage, session_id, timestamp, evidence}
        self.stage_evidence: List[Dict] = []

class AttackChainEngine:
    def __init__(self, temporal_window_hours: int = 24):
        self.temporal_window = timedelta(hours=temporal_window_hours)
        
    def _calculate_score(self, chain: AttackChainState) -> float:
        """
        Bounded 0-100 logic evaluating progression maturity.
        Do not just sum up scores blindly; bound the progression mathematically.
        """
        stages = {AttackStage(s) for s in chain.stages_hit} - {AttackStage.UNKNOWN}
        if not stages:
            return 0.0

        # Peak: how far along the kill chain the user got, damped until several distinct
        # stages corroborate it (one exfil-looking command alone is not a campaign).
        max_severity = max(get_stage_severity(s) for s in stages)
        breadth = min(1.0, len(stages) / 4.0)
        peak = (max_severity / 10.0) * breadth

        # Coverage: severity-weighted share of the whole kill chain observed.
        all_stages = [s for s in AttackStage if s != AttackStage.UNKNOWN]
        coverage = sum(get_stage_severity(s) for s in stages) / sum(get_stage_severity(s) for s in all_stages)

        # Reaches 100 only when every stage is present, so chains stay comparable.
        return round(100.0 * (0.5 * peak + 0.5 * coverage), 1)
        
    def process_event(self, active_chain: Optional[AttackChainState], user_id: str, session_id: str, stage: AttackStage, timestamp: datetime, evidence: Optional[str] = None) -> AttackChainState:
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
            # current_stage tracks the latest activity; stages_hit keeps each stage once,
            # in first-seen order, so repeats don't inflate length or confidence
            active_chain.current_stage = stage.value
            if stage.value not in active_chain.stages_hit:
                active_chain.stages_hit.append(stage.value)
                active_chain.stage_evidence.append({
                    "stage": stage.value, "session_id": session_id,
                    "timestamp": timestamp.isoformat(), "evidence": evidence,
                })
                
        if not active_chain.related_sessions or active_chain.related_sessions[-1] != session_id:
            active_chain.related_sessions.append(session_id)
        active_chain.risk_score = self._calculate_score(active_chain)
        
        # Bounding confidence
        active_chain.confidence = min(0.2 + (len(active_chain.stages_hit) * 0.15), 1.0)
        
        return active_chain
