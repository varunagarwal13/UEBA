"""
HDBSCAN-based peer deviation engine.

Clusters (user, day) BEHAVIORAL SUMMARIES -- not individual events --
in absolute feature space (not self-relative "surprise" like ECOD).
The question this engine answers is "does this user's day look like
anyone else's", not "is this unusual for THIS user" -- that's a
genuinely different signal than ECOD provides, which is the point of
having both engines.

Streaming design: score() is called per-EVENT, but the underlying
model reasons about whole DAYS. The engine keeps a running, in-memory
accumulator per (user, date) that updates as events arrive, and scores
the user's CURRENT, partial day against the fitted peer clusters via
hdbscan.approximate_predict -- the standard way to score new points
against an already-fit HDBSCAN model. GLOSH (outlier_scores_) only
exists for the original training points, so approximate_predict's
membership strength is the correct live equivalent, not a shortcut.

Design choices worth knowing:
- PIVOT_ACCOUNTS are excluded from defining cluster centers (their
  days would distort what "normal peer behavior" looks like) but are
  still scored against the resulting clusters at inference time.
- `variance` scales with (1 - membership_strength) -- a day that
  confidently belongs to a cluster is trusted more than one sitting
  ambiguously between clusters, or flagged as pure noise (label -1).
- Like ECOD, `score` here is a reasonable 0-100 proxy, not yet the
  final calibrated value -- formal calibration against labels happens
  in a separate later step.
"""

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

import hdbscan
import numpy as np
from sklearn.preprocessing import StandardScaler

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput
from src.ingest.spedia import PIVOT_ACCOUNTS

DAY_FEATURE_NAMES = (
    "total_events", "command_exec_count", "file_op_count",
    "http_count", "email_count", "usb_connect_count", "hour_spread",
)


def _empty_day_accumulator() -> dict:
    return {
        "total_events": 0,
        "command_exec_count": 0,
        "file_op_count": 0,
        "http_count": 0,
        "email_count": 0,
        "usb_connect_count": 0,
        "hours": [],
    }


def _update_accumulator(acc: dict, event: Event) -> None:
    acc["total_events"] += 1
    if event.event_type == "command_exec":
        acc["command_exec_count"] += 1
    elif event.event_type == "file_op":
        acc["file_op_count"] += 1
    elif event.event_type == "http":
        acc["http_count"] += 1
    elif event.event_type == "email_send":
        acc["email_count"] += 1
    elif event.event_type == "usb_connect":
        acc["usb_connect_count"] += 1
    acc["hours"].append(event.timestamp.hour)


def _accumulator_to_vector(acc: dict) -> np.ndarray:
    hour_spread = (max(acc["hours"]) - min(acc["hours"])) if acc["hours"] else 0
    return np.array(
        [
            acc["total_events"],
            acc["command_exec_count"],
            acc["file_op_count"],
            acc["http_count"],
            acc["email_count"],
            acc["usb_connect_count"],
            hour_spread,
        ],
        dtype=float,
    )


def _build_day_vectors(events: List[Event]) -> Dict[Tuple[str, date], np.ndarray]:
    accumulators: Dict[Tuple[str, date], dict] = defaultdict(_empty_day_accumulator)
    for e in events:
        key = (e.user_id, e.timestamp.date())
        _update_accumulator(accumulators[key], e)
    return {key: _accumulator_to_vector(acc) for key, acc in accumulators.items()}


class HDBSCANEngine(DetectionEngine):
    def __init__(self, min_cluster_size: int = 5) -> None:
        self.min_cluster_size = min_cluster_size
        self.scaler: Optional[StandardScaler] = None
        self.clusterer: Optional["hdbscan.HDBSCAN"] = None
        # Live running accumulators per (user, date). Resetting these
        # across separate evaluation runs (e.g. baseline vs. campaign
        # period) is the caller's responsibility -- see reset_running().
        self._running: Dict[Tuple[str, date], dict] = defaultdict(_empty_day_accumulator)

    def reset_running(self) -> None:
        """Clear the live per-day accumulators. Call this between
        separate evaluation passes (e.g. before scoring the campaign
        period) so yesterday's partial-day state doesn't bleed in."""
        self._running = defaultdict(_empty_day_accumulator)

    def fit(self, history: List[Event]) -> None:
        day_vectors = _build_day_vectors([e for e in history if e.user_id not in PIVOT_ACCOUNTS])
        if len(day_vectors) < self.min_cluster_size:
            raise ValueError(
                f"HDBSCANEngine.fit() needs at least {self.min_cluster_size} "
                f"(user, day) windows, got {len(day_vectors)}"
            )

        X = np.vstack(list(day_vectors.values()))
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.clusterer = hdbscan.HDBSCAN(min_cluster_size=self.min_cluster_size, prediction_data=True)
        self.clusterer.fit(X_scaled)

    def score(self, user_id: str, event: Event) -> EngineOutput:
        if self.clusterer is None or self.scaler is None:
            raise RuntimeError("HDBSCANEngine.score() called before fit()")

        key = (user_id, event.timestamp.date())
        _update_accumulator(self._running[key], event)
        vector = _accumulator_to_vector(self._running[key]).reshape(1, -1)
        vector_scaled = self.scaler.transform(vector)

        labels, strengths = hdbscan.approximate_predict(self.clusterer, vector_scaled)
        label = int(labels[0])
        strength = float(strengths[0])

        if label == -1:
            score = 100.0
            variance = 1.0
            explanation = "Day-so-far doesn't match any peer cluster (noise)"
        else:
            score = max(0.0, min(100.0, (1.0 - strength) * 100.0))
            variance = max(1.0 - strength, 0.01)
            explanation = f"Peer-cluster membership strength {strength:.2f}"

        return EngineOutput(score=score, variance=variance, explanation=explanation)
