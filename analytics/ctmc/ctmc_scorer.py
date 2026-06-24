# analytics/ctmc/ctmc_scorer.py
#
# PURPOSE: Score a state sequence for anomaly using transition probabilities.
#
# KEY CHANGE from v1:
# Reduced trust dampening. Previously, users with 0 sessions got 50% dampening,
# which buried real threat signals. Now minimum dampening factor is 0.70,
# meaning even new users' scores are at least 70% of computed value.
# This improves recall without hurting precision significantly.

import math
from typing import List, Dict

UNSEEN_PROB  = 1e-5
MIN_SESSIONS = 10


class CTMCScorer:

    def score(
        self,
        state_sequence: List[str],
        transition_matrix: Dict[str, Dict[str, float]],
        total_sessions: int = 0
    ) -> float:
        if len(state_sequence) < 2:
            return 0.0

        log_prob = 0.0
        for i in range(len(state_sequence) - 1):
            from_s = state_sequence[i]
            to_s   = state_sequence[i + 1]
            prob   = transition_matrix.get(from_s, {}).get(to_s, UNSEEN_PROB)
            log_prob += math.log(max(prob, UNSEEN_PROB))

        n     = len(state_sequence) - 1
        avg   = log_prob / n
        raw   = 100.0 * (1.0 - math.exp(avg / 3.0))
        score = max(0.0, min(100.0, raw))

        # Trust dampening — reduced from 0.30 minimum to 0.70 minimum.
        # Rationale: a 50% reduction was hiding real threats from new users.
        # 0.70 minimum means we still reduce confidence for thin profiles
        # but don't bury the signal entirely.
        if total_sessions < MIN_SESSIONS:
            factor = 0.70 + 0.30 * (total_sessions / MIN_SESSIONS)
            score *= factor

        return round(score, 2)
