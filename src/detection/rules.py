"""
Rule engine: deterministic if-this-then-that checks, mined against
SPEDIA's labeled malicious sequences.

Owner: TODO assign a name. Start by mining 5-10 candidate rules from
the labeled attack narrative (e.g. usb_connect followed by bulk file
copy followed by delete, all within N minutes) and check precision/
recall of each rule against the labels before wiring it in here.
"""

from typing import List

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput


class RuleEngine(DetectionEngine):
    def __init__(self) -> None:
        self.rules: list = []  # TODO: list of (name, predicate_fn, precision) tuples

    def fit(self, history: List[Event]) -> None:
        # Rules are usually hand-authored / mined offline, not "trained"
        # in the statistical sense — but use this to load thresholds
        # derived from `history` if any rule needs a baseline (e.g.
        # "more than N standard deviations above this user's normal
        # file-access count").
        raise NotImplementedError

    def score(self, user_id: str, event: Event) -> EngineOutput:
        raise NotImplementedError
