# analytics/risk_scoring/risk_scorer.py
#
# CHANGES FROM v1:
#   Weights unchanged: CTMC=0.60, Rules=0.40
#   Agreement boost threshold lowered from 60 to 40
#   so more sessions get the multi-signal confidence boost.
#   Confidence calculation improved — penalizes single-signal
#   alerts more aggressively to reduce false positives.

from typing import List
from dataclasses import dataclass
from analytics.rule_engine.rule_engine import RuleViolation

CTMC_WEIGHT  = 0.60
RULES_WEIGHT = 0.40

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
    ctmc_score: float
    rule_score: float
    if_score:   float
    confidence: float


class RiskScorer:

    def compute(
        self,
        user_id:        str,
        session_id:     str,
        ctmc_score:     float,
        violations:     List[RuleViolation],
        total_sessions: int,
        if_score:       float = 0.0,
    ) -> RiskResult:

        rule_score = min(100.0, sum(v.score_contribution for v in violations))
        risk_score = CTMC_WEIGHT * ctmc_score + RULES_WEIGHT * rule_score
        risk_score = max(0.0, min(100.0, risk_score))

        # Agreement boost: when both CTMC AND rules fire above 40,
        # we have two independent signals agreeing — boost confidence
        if ctmc_score >= 40 and rule_score >= 40:
            boost = (ctmc_score + rule_score) / 200.0 * 12.0
            risk_score = min(100.0, risk_score + boost)

        # Severity
        severity = "Low"
        for sev, threshold in SEVERITY_THRESHOLDS.items():
            if risk_score >= threshold:
                severity = sev
                break

        # Confidence
        confidence = 1.0
        if total_sessions < 5:
            confidence *= 0.55
        elif total_sessions < 15:
            confidence *= 0.80

        # Penalize single-signal alerts more to reduce false positives
        if ctmc_score > 50 and rule_score < 5:
            confidence *= 0.75   # CTMC fired but no rules — less confident
        elif rule_score > 50 and ctmc_score < 5:
            confidence *= 0.80   # Rules fired but CTMC disagrees — less confident

        return RiskResult(
            user_id=user_id, session_id=session_id,
            risk_score=round(risk_score, 1), severity=severity,
            ctmc_score=round(ctmc_score, 1),
            rule_score=round(rule_score, 1),
            if_score=0.0,
            confidence=round(confidence, 2),
        )
