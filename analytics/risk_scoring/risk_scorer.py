# analytics/risk_scoring/risk_scorer.py
from typing import List, Dict, Optional
from dataclasses import dataclass
from analytics.rule_engine.rule_engine import RuleViolation

SEVERITY_THRESHOLDS = {
    "Critical": 90,
    "High":     70,
    "Medium":   40,
    "Low":       0,
}

@dataclass
class RiskResult:
    user_id:    str
    session_id: str
    risk_score: float
    severity:   str
    ctmc_score: Optional[float]
    rule_score: Optional[float]
    if_score:   Optional[float]
    confidence: float
    personal_baseline_score: Optional[float] = None
    attack_chain_score: Optional[float] = None
    comm_score: Optional[float] = None
    trend_score: Optional[float] = None

class RiskScorer:
    """
    Central Risk Fusion Engine.
    V2 natively supports dynamic weights to prevent hard-coding untested heuristics.
    """
    def __init__(self, default_weights: Optional[Dict[str, float]] = None):
        if default_weights is None:
            # V2.1 base weights
            self.weights = {"ctmc": 0.30, "rules": 0.20, "if": 0.20, "baseline": 0.15, "attack_chain": 0.15, "comm": 1.0, "trend": 1.0}
        else:
            self.weights = default_weights
            
    def compute(
        self,
        user_id:        str,
        session_id:     str,
        violations:     List[RuleViolation],
        total_sessions: int,
        ctmc_score:     Optional[float] = None,
        if_score:       Optional[float] = None,
        personal_baseline_score: Optional[float] = None,
        attack_chain_score: Optional[float] = None,
        comm_score:     Optional[float] = None,
        trend_score:    Optional[float] = None
    ) -> RiskResult:

        rule_score = min(100.0, sum(v.score_contribution for v in violations)) if violations is not None else None
        
        # Phase 5: Dynamic Weight Normalization
        base_signals = {
            "ctmc": ctmc_score,
            "rules": rule_score,
            "if": if_score,
            "baseline": personal_baseline_score,
            "attack_chain": attack_chain_score
        }
        
        active_weight_sum = sum(self.weights[k] for k, v in base_signals.items() if v is not None)
        
        risk_score = 0.0
        if active_weight_sum > 0:
            for k, v in base_signals.items():
                if v is not None:
                    normalized_weight = self.weights[k] / active_weight_sum
                    risk_score += normalized_weight * v
                    
        risk_score = max(0.0, min(100.0, risk_score))

        # Additive situational penalties
        # Comm score and Trend score are added on top of the base probability (max capped to 100)
        additive_bonus = (self.weights.get("comm", 0.0) * comm_score) + (self.weights.get("trend", 0.0) * trend_score)
        risk_score = min(100.0, risk_score + additive_bonus)

        # Agreement boost (inherited from V1)
        # We only boost if multiple independent fundamental signals fire
        signals = [s for s in [ctmc_score, rule_score, if_score] if s >= 40]
        if len(signals) >= 2:
            boost = sum(signals) / (len(signals) * 100.0) * 12.0
            risk_score = min(100.0, risk_score + boost)

        # Severity
        severity = "Low"
        for sev, threshold in SEVERITY_THRESHOLDS.items():
            if risk_score >= threshold:
                severity = sev
                break

        # Phase 11: Evidence-Based Confidence Bounds
        
        # 1. Historical Data Penalty
        confidence = 1.0
        if total_sessions < 3:
            confidence -= 0.40  # Massively reduced trust for brand new users
        elif total_sessions < 10:
            confidence -= 0.15

        # 2. Model Pipeline Integrity Penalty
        if if_score is None:
            confidence -= 0.20
            
        # 3. Model Disagreement Penalty (Single-signal isolated detections)
        valid_scores = [s for s in [ctmc_score, rule_score, if_score, attack_chain_score, personal_baseline_score] if s is not None]
        if valid_scores:
            max_s = max(valid_scores)
            avg_s = sum(valid_scores) / len(valid_scores)
            if max_s > 60 and avg_s < (max_s / 3.0):
                confidence -= 0.15  # Triangulation failed, it's a completely isolated signal
                
        # 4. Multi-Signal Agreement Boost
        active_signals = sum(1 for s in valid_scores if s > 40)
        if active_signals >= 3:
            confidence += 0.20  # Extreme confidence when models natively confirm each other
            
        confidence = max(0.01, min(1.0, confidence))

        return RiskResult(
            user_id=user_id, session_id=session_id,
            risk_score=round(risk_score, 1), severity=severity,
            ctmc_score=round(ctmc_score, 1) if ctmc_score is not None else None,
            rule_score=round(rule_score, 1) if rule_score is not None else None,
            if_score=round(if_score, 1) if if_score is not None else None,
            confidence=round(confidence, 2),
            personal_baseline_score=round(personal_baseline_score, 1) if personal_baseline_score is not None else None,
            attack_chain_score=round(attack_chain_score, 1) if attack_chain_score is not None else None,
            comm_score=round(comm_score, 1) if comm_score is not None else None,
            trend_score=round(trend_score, 1) if trend_score is not None else None
        )
