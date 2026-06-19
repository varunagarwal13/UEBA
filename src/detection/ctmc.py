"""
CTMC: per-user continuous-time Markov chain over event_type states,
optionally modulated by time-of-day. Anomaly score = log-likelihood
ratio of the user's observed (state, dwell-time) sequence under their
own learned generator matrix Q vs. the role-level population Q.

Owner: TODO assign a name. This is the hardest engine in the MVP -
budget the most time here. variance should scale with 1/N_transitions
observed for that user (standard CTMC estimator variance).
"""

from typing import List

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput


class CTMCEngine(DetectionEngine):
    def __init__(self) -> None:
        self.states: list = []  # TODO: e.g. [login, file_access, command_exec, http_upload, email_send, usb_connect, logout]
        self.Q_per_user: dict = {}  # user_id -> generator matrix
        self.Q_population: dict = {}  # role -> population-level generator matrix
        self.transition_counts: dict = {}  # user_id -> count, drives variance

    def fit(self, history: List[Event]) -> None:
        raise NotImplementedError

    def score(self, user_id: str, event: Event) -> EngineOutput:
        raise NotImplementedError
