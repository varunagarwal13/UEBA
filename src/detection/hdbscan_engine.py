"""
HDBSCAN: clusters users (or user-days) in behavioral-feature space.
Peer deviation score = GLOSH outlier score relative to nearest cluster.

Owner: TODO assign a name. hdbscan library gives GLOSH scores for free
via outlier_scores_. variance should scale with (1 - soft cluster
membership probability) - an ambiguous point between two clusters is
less trustworthy than one sitting deep inside its cluster.
"""

from typing import List

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput


class HDBSCANEngine(DetectionEngine):
    def __init__(self) -> None:
        self.clusterer = None  # TODO: hdbscan.HDBSCAN instance

    def fit(self, history: List[Event]) -> None:
        raise NotImplementedError

    def score(self, user_id: str, event: Event) -> EngineOutput:
        raise NotImplementedError
