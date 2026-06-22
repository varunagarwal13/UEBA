"""
CTMC engine -- the architecture's centerpiece. Models each user's
activity as a continuous-time Markov chain over event_type states,
estimates a generator matrix Q via MLE from baseline transitions and
dwell times, and scores each new transition by how much better the
POPULATION's Q explains it than the user's OWN historical Q does --
plus a separate, additive penalty for transitions happening at an
hour this specific user normally isn't active.

Unlike ECOD (point-wise rarity) and HDBSCAN (local-window peer
comparison), this is the only engine that reasons about SEQUENCE --
doing things in an unusual order is exactly what this catches and the
other three structurally can't.

THE MATH, PRECISELY:

States = Event.event_type (9 states, matching
src.ingest.spedia._infer_event_type's taxonomy exactly).

For a continuous-time Markov chain, the log-likelihood of observing
"dwelt in state i for time t, then jumped to state j" is:
    log L = log(Q[i][j]) - q_i * t
where q_i = -Q[i][i] = sum_{k!=i} Q[i][k] is the total exit rate from
state i (standard exponential-holding-time + categorical-jump-target
CTMC likelihood).

Q[i][j] is estimated via MLE: (observed transitions i->j) / (total
time spent in state i), with Laplace-style smoothing so a transition
never seen in baseline gets a small nonzero rate instead of log(0).

The base anomaly signal for one transition is:
    base_ratio = log L(transition | Q_population) - log L(transition | Q_user)
Higher (more positive) = the population's generic pattern explains
this transition BETTER than the user's own history does.

TIME-OF-DAY MODULATION -- DESIGN HISTORY WORTH KNOWING:
The first version multiplied BOTH Q_user's and Q_population's rates by
hour-likelihood multipliers and took the ratio. That was broken in two
different ways, found by testing rather than assumed away: (1) using
the SAME multiplier on both sides makes log(mult) cancel exactly in
the subtraction, making time-of-day invisible to the score; (2) fixing
that by giving each side its OWN multiplier introduced a different bug
-- the interaction between two independently-smoothed hour
distributions flipped the sign in some configurations (3am scoring as
MORE normal than 9am). Rather than keep patching an increasingly
fragile multiplicative scheme, this version uses a SEPARATE, simply-
signed ADDITIVE penalty instead:
    hour_penalty = -log(hour_of_day_likelihood(user_profile, hour) * 24)
This is unambiguous: 0 at a perfectly average hour, positive (adds
anomaly) at an hour this user rarely operates, negative (subtracts
anomaly) at their typically busiest hour. final ratio = base_ratio +
HOUR_WEIGHT * hour_penalty.

CAVEAT carried over regardless of design version: a basic exponential-
holding-time model makes SHORTER dwell times always more likely than
longer ones for any fixed rate, so this model does not by itself flag
"things happened too fast". That signal lives in HDBSCAN's
window_duration feature -- these two engines are complementary.

`variance` scales with 1/(1+N_transitions) observed for that user
during baseline fitting.

set use_time_modulation=False to get a plain (unmodulated) Markov
chain -- the ablation: does the hour penalty earn its complexity?
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput
from src.ingest.spedia import PIVOT_ACCOUNTS
from src.profile.build import UserProfile, build_profiles, hour_of_day_likelihood

STATES = (
    "login", "logout", "login_failed", "command_exec",
    "file_op", "http", "email_send", "usb_connect", "unknown",
)
STATE_INDEX = {s: i for i, s in enumerate(STATES)}
N_STATES = len(STATES)

SMOOTHING_ALPHA = 0.5  # pseudo-count added to transition counts
SMOOTHING_TIME = 1.0  # seconds added to the time-in-state denominator
MIN_DWELL_SECONDS = 1.0  # floor for degenerate near-zero gaps
HOUR_WEIGHT = 1.0  # weight of the additive hour penalty relative to base_ratio


def _estimate_Q(transition_counts: np.ndarray, time_in_state: np.ndarray) -> np.ndarray:
    """transition_counts: N_STATES x N_STATES observed counts.
    time_in_state: N_STATES total seconds spent in each state.
    Returns the smoothed generator matrix (off-diagonal = rates,
    diagonal = -row_sum, so every row sums to zero)."""
    Q = np.zeros((N_STATES, N_STATES))
    for i in range(N_STATES):
        denom = time_in_state[i] + SMOOTHING_TIME
        for j in range(N_STATES):
            if i == j:
                continue
            Q[i, j] = (transition_counts[i, j] + SMOOTHING_ALPHA) / denom
        Q[i, i] = -Q[i].sum()
    return Q


def _accumulate_transitions(events: List[Event]) -> Tuple[np.ndarray, np.ndarray, int]:
    """events must already be sorted by timestamp. Returns
    (transition_counts, time_in_state, n_transitions)."""
    transition_counts = np.zeros((N_STATES, N_STATES))
    time_in_state = np.zeros(N_STATES)
    n_transitions = 0

    for a, b in zip(events, events[1:]):
        i = STATE_INDEX.get(a.event_type, STATE_INDEX["unknown"])
        j = STATE_INDEX.get(b.event_type, STATE_INDEX["unknown"])
        dwell = max((b.timestamp - a.timestamp).total_seconds(), MIN_DWELL_SECONDS)
        transition_counts[i, j] += 1
        time_in_state[i] += dwell
        n_transitions += 1

    return transition_counts, time_in_state, n_transitions


def _transition_log_likelihood(Q: np.ndarray, i: int, j: int, dwell: float) -> float:
    """Plain (unmodulated) CTMC transition log-likelihood."""
    rate_ij = Q[i, j]
    exit_rate_i = -Q[i, i]
    if rate_ij <= 0:
        rate_ij = 1e-12  # guards log(0); shouldn't trigger given smoothing
    return float(np.log(rate_ij) - exit_rate_i * dwell)


def _hour_penalty(profile: Optional[UserProfile], hour: int) -> float:
    """0 at a perfectly average hour for this user, positive (more
    anomalous) at an hour they rarely operate, negative (less
    anomalous) at their typically busiest hour."""
    if profile is None or profile.n_events == 0:
        return 0.0
    mult = hour_of_day_likelihood(profile, hour) * 24.0
    mult = max(mult, 1e-9)
    return -float(np.log(mult))


class CTMCEngine(DetectionEngine):
    def __init__(self, use_time_modulation: bool = True) -> None:
        self.use_time_modulation = use_time_modulation
        self.profiles: Dict[str, UserProfile] = {}
        self.Q_user: Dict[str, np.ndarray] = {}
        self.n_transitions_user: Dict[str, int] = {}
        self.Q_population: Optional[np.ndarray] = None
        self._last_event: Dict[str, Event] = {}
        self._train_ratio_scores: Optional[np.ndarray] = None

    def reset_running(self) -> None:
        """Clear per-user 'last seen event' state. Call between
        separate evaluation passes (e.g. before scoring the campaign
        period) for the same reason as HDBSCANEngine.reset_running()."""
        self._last_event = {}

    def _ratio_for(self, user_id: str, i: int, j: int, dwell: float, hour: int) -> float:
        Q_u = self.Q_user.get(user_id, self.Q_population)
        base_ratio = _transition_log_likelihood(self.Q_population, i, j, dwell) - _transition_log_likelihood(
            Q_u, i, j, dwell
        )
        if not self.use_time_modulation:
            return base_ratio
        profile = self.profiles.get(user_id)
        return base_ratio + HOUR_WEIGHT * _hour_penalty(profile, hour)

    def fit(self, history: List[Event]) -> None:
        self.profiles = build_profiles(history)

        by_user: Dict[str, List[Event]] = defaultdict(list)
        for e in history:
            if e.user_id not in PIVOT_ACCOUNTS:
                by_user[e.user_id].append(e)
        for user_id in by_user:
            by_user[user_id].sort(key=lambda e: e.timestamp)

        pop_counts = np.zeros((N_STATES, N_STATES))
        pop_time = np.zeros(N_STATES)

        for user_id, user_events in by_user.items():
            counts, time_in_state, n_trans = _accumulate_transitions(user_events)
            self.Q_user[user_id] = _estimate_Q(counts, time_in_state)
            self.n_transitions_user[user_id] = n_trans
            pop_counts += counts
            pop_time += time_in_state

        self.Q_population = _estimate_Q(pop_counts, pop_time)

        # Reference distribution for percentile-rank scaling: replay
        # every baseline transition through the same scoring logic
        # score() uses, same pattern as ECODEngine.
        ratio_scores = []
        for user_id, user_events in by_user.items():
            for a, b in zip(user_events, user_events[1:]):
                i = STATE_INDEX.get(a.event_type, STATE_INDEX["unknown"])
                j = STATE_INDEX.get(b.event_type, STATE_INDEX["unknown"])
                dwell = max((b.timestamp - a.timestamp).total_seconds(), MIN_DWELL_SECONDS)
                ratio_scores.append(self._ratio_for(user_id, i, j, dwell, b.timestamp.hour))

        self._train_ratio_scores = np.array(ratio_scores) if ratio_scores else np.array([0.0])

    def score(self, user_id: str, event: Event) -> EngineOutput:
        if self.Q_population is None:
            raise RuntimeError("CTMCEngine.score() called before fit()")

        prev = self._last_event.get(user_id)
        self._last_event[user_id] = event

        if prev is None:
            return EngineOutput(score=0.0, variance=1.0, explanation="No prior event yet for this user")

        i = STATE_INDEX.get(prev.event_type, STATE_INDEX["unknown"])
        j = STATE_INDEX.get(event.event_type, STATE_INDEX["unknown"])
        dwell = max((event.timestamp - prev.timestamp).total_seconds(), MIN_DWELL_SECONDS)

        ratio = self._ratio_for(user_id, i, j, dwell, event.timestamp.hour)

        percentile = float((self._train_ratio_scores < ratio).mean()) * 100.0
        score = max(0.0, min(100.0, percentile))

        n_trans = self.n_transitions_user.get(user_id, 0)
        variance = 1.0 / (1.0 + n_trans)

        return EngineOutput(
            score=score,
            variance=variance,
            explanation=f"{prev.event_type}->{event.event_type} transition, {score:.1f} percentile vs. baseline",
        )
