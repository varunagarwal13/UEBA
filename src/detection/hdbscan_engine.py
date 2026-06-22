"""
HDBSCAN-based peer deviation engine -- v2, sliding K-event windows.

v1 clustered on whole-DAY summaries. Real evaluation against SPEDIA's
campaign period showed this washed out single anomalous actions buried
inside an otherwise-normal day: ROC-AUC collapsed to ~0.51-0.56 once
identity-coded accounts were excluded from the test population, while
ECOD (which scores point-wise, not day-aggregated) held at ~0.82. This
version replaces day-level aggregation with a SLIDING window of the
last WINDOW_SIZE events per user, recomputed at every score() call --
a single unusual action only has to stand out against its immediate
local context, not get averaged across an entire day.

Windows can span midnight (no artificial day-boundary splitting of a
continuous burst) and naturally shrink during a user's cold-start
period (fewer than WINDOW_SIZE events seen so far) -- both are
intentional, not edge cases to special-case away.

Design choices carried over from v1, unchanged:
- PIVOT_ACCOUNTS excluded from defining cluster centers, still scored
  against the resulting clusters.
- `variance` scales with (1 - membership_strength).
- `score` is a 0-100 proxy via approximate_predict, not yet the final
  calibrated value -- formal calibration against labels is a separate
  later step.

New in this version: `window_duration_seconds`, the real elapsed time
covered by the window. This wasn't meaningful at day-granularity
(every window was ~24h by definition) but at 10-event granularity it
directly captures burstiness -- "10 events in 4 minutes" (likely an
automated/scripted action) looks very different from "10 events
spread across 6 hours" (normal human pacing), which is exactly the
kind of signature an attack script tends to leave.
"""

from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional

import hdbscan
import numpy as np
from sklearn.preprocessing import StandardScaler

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput
from src.ingest.spedia import PIVOT_ACCOUNTS

DEFAULT_WINDOW_SIZE = 10  # events per window
DEFAULT_TRAIN_STRIDE = 3  # step size for overlapping training windows


def _window_to_vector(window: List[Event]) -> np.ndarray:
    counts = {"command_exec": 0, "file_op": 0, "http": 0, "email_send": 0, "usb_connect": 0}
    hours: List[int] = []
    for e in window:
        if e.event_type in counts:
            counts[e.event_type] += 1
        hours.append(e.timestamp.hour)

    hour_spread = (max(hours) - min(hours)) if hours else 0
    duration = (window[-1].timestamp - window[0].timestamp).total_seconds() if len(window) > 1 else 0.0

    return np.array(
        [
            len(window),
            counts["command_exec"],
            counts["file_op"],
            counts["http"],
            counts["email_send"],
            counts["usb_connect"],
            hour_spread,
            duration,
        ],
        dtype=float,
    )


def _build_training_windows(events: List[Event], window_size: int, stride: int) -> List[np.ndarray]:
    """Per user, slide a window across their own chronological event
    sequence (never mixing users within a window). Users with fewer
    than window_size events contribute one partial window covering
    their whole baseline history, rather than nothing."""
    by_user: Dict[str, List[Event]] = defaultdict(list)
    for e in events:
        by_user[e.user_id].append(e)

    vectors = []
    for user_events in by_user.values():
        user_events = sorted(user_events, key=lambda e: e.timestamp)
        if len(user_events) <= window_size:
            vectors.append(_window_to_vector(user_events))
            continue
        for start in range(0, len(user_events) - window_size + 1, stride):
            vectors.append(_window_to_vector(user_events[start : start + window_size]))
    return vectors


class HDBSCANEngine(DetectionEngine):
    def __init__(
        self,
        min_cluster_size: int = 5,
        window_size: int = DEFAULT_WINDOW_SIZE,
        train_stride: int = DEFAULT_TRAIN_STRIDE,
    ) -> None:
        self.min_cluster_size = min_cluster_size
        self.window_size = window_size
        self.train_stride = train_stride
        self.scaler: Optional[StandardScaler] = None
        self.clusterer: Optional["hdbscan.HDBSCAN"] = None
        self._running: Dict[str, Deque[Event]] = defaultdict(lambda: deque(maxlen=self.window_size))

    def reset_running(self) -> None:
        """Clear the live per-user sliding windows. Call this between
        separate evaluation passes (e.g. before scoring the campaign
        period) so baseline-period tail events don't bleed into the
        first window scored."""
        self._running = defaultdict(lambda: deque(maxlen=self.window_size))

    def fit(self, history: List[Event]) -> None:
        non_pivot = [e for e in history if e.user_id not in PIVOT_ACCOUNTS]
        vectors = _build_training_windows(non_pivot, self.window_size, self.train_stride)
        if len(vectors) < self.min_cluster_size:
            raise ValueError(
                f"HDBSCANEngine.fit() needs at least {self.min_cluster_size} "
                f"training windows, got {len(vectors)}"
            )

        X = np.vstack(vectors)
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.clusterer = hdbscan.HDBSCAN(min_cluster_size=self.min_cluster_size, prediction_data=True)
        self.clusterer.fit(X_scaled)

    def score(self, user_id: str, event: Event) -> EngineOutput:
        if self.clusterer is None or self.scaler is None:
            raise RuntimeError("HDBSCANEngine.score() called before fit()")

        self._running[user_id].append(event)
        window = list(self._running[user_id])
        vector = _window_to_vector(window).reshape(1, -1)
        vector_scaled = self.scaler.transform(vector)

        labels, strengths = hdbscan.approximate_predict(self.clusterer, vector_scaled)
        label = int(labels[0])
        strength = float(strengths[0])

        if label == -1:
            score = 100.0
            variance = 1.0
            explanation = "Recent activity doesn't match any peer cluster (noise)"
        else:
            score = max(0.0, min(100.0, (1.0 - strength) * 100.0))
            variance = max(1.0 - strength, 0.01)
            explanation = f"Peer-cluster membership strength {strength:.2f} (last {len(window)} events)"

        return EngineOutput(score=score, variance=variance, explanation=explanation)
