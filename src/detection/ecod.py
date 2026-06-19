"""
ECOD: empirical-CDF outlier scoring, per feature, aggregated.

Owner: TODO assign a name. pyod.models.ecod.ECOD does the heavy lifting -
this class is mostly about feature selection (which per-user behavioral
features to feed it) and wiring its output into our EngineOutput shape.
variance should scale with how few samples back a given feature's ECDF
estimate for that user.
"""

from typing import List

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput


class ECODEngine(DetectionEngine):
    def __init__(self) -> None:
        self.model = None  # TODO: pyod ECOD instance per feature set
        self.n_samples_per_user: dict = {}

    def fit(self, history: List[Event]) -> None:
        raise NotImplementedError

    def score(self, user_id: str, event: Event) -> EngineOutput:
        raise NotImplementedError
