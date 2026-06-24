import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from analytics.state_extraction.state_extractor import StateExtractor
from analytics.ctmc.ctmc_scorer import CTMCScorer
from analytics.rule_engine.rule_engine import RuleEngine
from analytics.risk_scoring.risk_scorer import RiskScorer

ALERT_THRESHOLD    = 5.0
MIN_SESSION_LENGTH = 3


class AnalyticsPipeline:

    def __init__(self, population_matrix: Dict[str, Dict[str, float]]):
        self.population_matrix   = population_matrix
        self.user_matrices       = {}
        self.user_session_counts = {}
        self.state_extractor     = StateExtractor()
        self.ctmc_scorer         = CTMCScorer()
        self.rule_engine         = RuleEngine()
        self.risk_scorer         = RiskScorer()

    def process_session(self, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user_id    = session.get("user_id", "unknown")
        session_id = session.get("session_id", "unknown")

        states = self.state_extractor.extract_states(session)
        if len(states) < MIN_SESSION_LENGTH:
            return None

        matrix         = self.user_matrices.get(user_id, self.population_matrix)
        total_sessions = self.user_session_counts.get(user_id, 0)

        ctmc_score = self.ctmc_scorer.score(states, matrix, total_sessions)
        violations = self.rule_engine.check_all_rules(
            states, session.get("events", []), user_id=user_id
        )
        result = self.risk_scorer.compute(
            user_id=user_id, session_id=session_id,
            ctmc_score=ctmc_score, violations=violations,
            total_sessions=total_sessions,
        )

        if result.risk_score < ALERT_THRESHOLD:
            return None

        alert_id = f"ALT{str(uuid.uuid4())[:8].upper()}"
        return {
            "alert": {
                "alert_id":       alert_id,
                "user_id":        user_id,
                "risk_score":     result.risk_score,
                "severity":       result.severity,
                "detection_type": "CTMC+RULES",
                "confidence":     result.confidence,
                "timestamp":      datetime.utcnow().isoformat() + "Z",
            },
            "explanation": {
                "alert_id": alert_id,
                "reasons":  [v.description for v in violations],
                "summary": (
                    f"User {user_id} triggered a {result.severity.lower()} "
                    f"risk alert. CTMC={result.ctmc_score}, "
                    f"Rules={result.rule_score}."
                ),
            },
            "model_breakdown": {
                "ctmc_score": result.ctmc_score,
                "rule_score": result.rule_score,
                "if_score":   0.0,
                "rule_violations": [
                    {"rule_id": v.rule_id, "rule_name": v.rule_name,
                     "severity": v.severity}
                    for v in violations
                ],
            },
            "timeline": {
                "user_id":  user_id,
                "timeline": states,
            },
        }
