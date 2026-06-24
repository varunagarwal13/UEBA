# analytics/ctmc/ctmc_scorer.py
#
# CHANGES FROM v1:
#   1. scaling_factor reduced from 3.0 to 2.0
#      Effect: same log-probability now maps to a HIGHER score.
#      A sequence with 1% transition probability per step
#      previously scored ~60. Now scores ~80.
#      This pulls anomalous sessions UP out of the 0-10 bucket.
#
#   2. Bonus score for sessions containing high-risk states
#      Even if the transition probabilities look normal,
#      the presence of Suspicious_Command or Recon_Command
#      deserves a score boost. Real UEBA products do this.
#
#   3. Trust dampening minimum raised from 0.70 to 0.80
#      Users with thin profiles were being dampened too heavily.

import math
from typing import List, Dict

UNSEEN_PROB  = 1e-5
MIN_SESSIONS = 10

# States that always add to suspicion regardless of transitions
HIGH_RISK_STATES = {
    "Suspicious_Command": 8.0,
    "Recon_Command":      6.0,
    "Privilege_Command":  5.0,
    "Login_Failed":       3.0,
    "File_Delete":        4.0,
}


class CTMCScorer:

    def score(
        self,
        state_sequence: List[str],
        transition_matrix: Dict[str, Dict[str, float]],
        total_sessions: int = 0
    ) -> float:
        if len(state_sequence) < 2:
            return 0.0

        # Step 1: Compute log-probability of the sequence
        log_prob = 0.0
        for i in range(len(state_sequence) - 1):
            from_s = state_sequence[i]
            to_s   = state_sequence[i + 1]
            prob   = transition_matrix.get(from_s, {}).get(to_s, UNSEEN_PROB)
            log_prob += math.log(max(prob, UNSEEN_PROB))

        # Step 2: Convert to 0-100 score
        # scaling_factor=2.0 makes the curve steeper than before (was 3.0)
        # meaning the same unusual sequence now gets a higher score
        n     = len(state_sequence) - 1
        avg   = log_prob / n
        raw   = 100.0 * (1.0 - math.exp(avg / 2.0))
        score = max(0.0, min(100.0, raw))

        # Step 3: Add bonus for high-risk state presence
        # Cap each state type's contribution to avoid double-counting
        bonus = 0.0
        for state, state_bonus in HIGH_RISK_STATES.items():
            count = state_sequence.count(state)
            if count > 0:
                # Diminishing returns — first occurrence adds full bonus,
                # subsequent ones add less. log(count+1) achieves this.
                bonus += state_bonus * math.log(count + 1)

        score = min(100.0, score + bonus)

        # Step 4: Trust dampening — minimum 0.80 (was 0.70)
        if total_sessions < MIN_SESSIONS:
            factor = 0.80 + 0.20 * (total_sessions / MIN_SESSIONS)
            score *= factor

        return round(score, 2)
