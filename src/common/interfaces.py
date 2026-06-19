"""
Every detection engine (rules, ecod, hdbscan, ctmc) implements this contract.

This is the actual coordination mechanism for the team: as long as your
engine subclasses DetectionEngine and implements fit() + score(), the
fusion layer can call it without knowing anything about how it works
internally. Build CTMC however you want inside the class — the outside
world only ever sees fit() and score().
"""

from abc import ABC, abstractmethod
from typing import List

from src.common.schema import Event, EngineOutput


class DetectionEngine(ABC):
    @abstractmethod
    def fit(self, history: List[Event]) -> None:
        """Build whatever baseline this engine needs (per-user stats, a
        cluster model, a transition-rate matrix, etc.) from historical events."""
        raise NotImplementedError

    @abstractmethod
    def score(self, user_id: str, event: Event) -> EngineOutput:
        """Score a single new event against the learned baseline for that user."""
        raise NotImplementedError
