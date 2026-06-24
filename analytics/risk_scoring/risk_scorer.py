# analytics/risk_scoring/risk_scorer.py
#
# PURPOSE: Combine CTMC score + rule violations into a final 0-100 risk score

from typing import List
from dataclasses import dataclass
from analytics.rule_engine.rule_engine import RuleViolation

CTMC_WEIGHT  = 0.60
RULES_WEIGHT = 0.40

SEVERITY_THRESHOLDS = {"Critical": 90, "High": 70, "Medium": 40, "Low": 0}


@dataclass
class RiskResult:
    user_id:    str
    session_id: str
    risk_score: float
    severity:   str
    ctmc_score: float
    rule_score: float
    confidence: float


class RiskScorer:

    def compute(
        self,
        user_id:        str,
        session_id:     str,
        ctmc_score:     float,
        violations:     List[RuleViolation],
        total_sessions: int,
    ) -> RiskResult:
        rule_score = min(100.0, sum(v.score_contribution for v in violations))
        risk_score = CTMC_WEIGHT * ctmc_score + RULES_WEIGHT * rule_score
        risk_score = max(0.0, min(100.0, risk_score))

        if ctmc_score >= 60 and rule_score >= 60:
            boost = (ctmc_score + rule_score) / 200.0 * 10.0
            risk_score = min(100.0, risk_score + boost)

        confidence = 1.0
        if total_sessions < 5:
            confidence *= 0.50
        elif total_sessions < 15:
            confidence *= 0.75
        if ctmc_score > 70 and rule_score < 10:
            confidence *= 0.85

        severity = "Low"
        for sev, threshold in SEVERITY_THRESHOLDS.items():
            if risk_score >= threshold:
                severity = sev
                break

        return RiskResult(
            user_id=user_id, session_id=session_id,
            risk_score=round(risk_score, 1), severity=severity,
            ctmc_score=round(ctmc_score, 1), rule_score=round(rule_score, 1),
            confidence=round(confidence, 2),
        )
