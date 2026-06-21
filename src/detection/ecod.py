"""
ECOD-based outlier engine.

Builds a parameter-free outlier score per event from three "surprise"
features derived from the per-user profile (src.profile.build): how
unusual the hour is, how rare this event_type is for this user, and
how rare the specific resource/command touched is for this user.

Design choices worth knowing:

- ONE global ECOD model fit across all (non-pivot) baseline users'
  feature vectors, not one model per user. Per-user features encode
  personalization (e.g. "how unusual is 3am FOR THIS USER"); ECOD
  then measures how extreme that personalized-surprise vector is
  relative to the whole population. This avoids the severe data-
  scarcity problem a per-user ECOD model would have for anyone with
  few baseline events.

- Deliberately excludes inter-event timing/dwell-time features --
  that's CTMC's job. ECOD here is purely point-wise/cross-sectional
  rarity, not sequence modeling. Splitting it this way keeps "is this
  hour weird" (ECOD) cleanly separate from "is this ORDER of actions
  weird" (CTMC) instead of both engines quietly modeling the same thing.

- `score` is scaled to 0-100 via percentile rank against the fitted
  training score distribution. That's a reasonable, monotonic proxy
  for "how extreme is this", not the final calibrated value -- true
  calibration (isotonic/Platt against labels) is a separate offline
  step applied on top of every engine's raw output before fusion.

- `variance` scales with 1/(1+n_events) for that user's profile --
  fewer baseline events backing their profile means less trust in
  what "normal" means for them, which is exactly the kind of signal
  inverse-variance fusion needs to downweight a noisy engine.
"""

import math
from typing import Dict, List, Optional

import numpy as np
from pyod.models.ecod import ECOD

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput
from src.ingest.spedia import PIVOT_ACCOUNTS
from src.profile.build import (
    UserProfile,
    _access_key,
    build_profiles,
    hour_of_day_likelihood,
)

# Must match the event_type taxonomy produced by src.ingest.spedia._infer_event_type
ALL_EVENT_TYPES = (
    "login", "logout", "login_failed", "command_exec",
    "file_op", "http", "email_send", "usb_connect", "unknown",
)


def _feature_vector(event: Event, profile: Optional[UserProfile]) -> np.ndarray:
    """3-dim surprise vector: [-log(hour likelihood), -log(event_type
    frequency), -log(access-target frequency)]. Higher = rarer for
    this specific user. Cold-start users (no profile, or an empty
    one) get a neutral mid-range vector rather than an artificially
    extreme one -- we don't actually know they're unusual, we just
    have no data."""
    if profile is None or profile.n_events == 0:
        return np.array([1.0, 1.0, 1.0])

    hour_p = hour_of_day_likelihood(profile, event.timestamp.hour)
    neg_log_hour = -math.log(hour_p)

    n_types = len(ALL_EVENT_TYPES)
    type_count = profile.event_type_counts.get(event.event_type, 0)
    type_freq = (type_count + 1) / (profile.n_events + n_types)
    neg_log_type = -math.log(type_freq)

    key = _access_key(event)
    if key is None:
        neg_log_access = 0.0  # no resource/command on this event -- no signal either way
    else:
        access_total = sum(profile.access_counts.values())
        access_count = profile.access_counts.get(key, 0)
        access_freq = (access_count + 1) / (access_total + 1)
        neg_log_access = -math.log(access_freq)

    return np.array([neg_log_hour, neg_log_type, neg_log_access])


class ECODEngine(DetectionEngine):
    def __init__(self) -> None:
        self.profiles: Dict[str, UserProfile] = {}
        self.model: Optional[ECOD] = None
        self._train_scores: Optional[np.ndarray] = None

    def fit(self, history: List[Event]) -> None:
        # Profiles built for everyone (pivot accounts included -- see
        # src.profile.build), but pivot-account EVENTS are excluded
        # from the ECOD training matrix: they'd teach the model that
        # "always anomalous" behavior is part of the normal population.
        self.profiles = build_profiles(history)

        rows = [
            _feature_vector(e, self.profiles.get(e.user_id))
            for e in history
            if e.user_id not in PIVOT_ACCOUNTS
        ]
        if not rows:
            raise ValueError("ECODEngine.fit() received no usable (non-pivot) training events")

        X = np.vstack(rows)
        self.model = ECOD()
        self.model.fit(X)
        self._train_scores = self.model.decision_scores_

    def score(self, user_id: str, event: Event) -> EngineOutput:
        if self.model is None:
            raise RuntimeError("ECODEngine.score() called before fit()")

        profile = self.profiles.get(user_id)
        x = _feature_vector(event, profile).reshape(1, -1)
        raw = float(self.model.decision_function(x)[0])

        percentile = float((self._train_scores < raw).mean()) * 100.0
        score = max(0.0, min(100.0, percentile))

        n_events = profile.n_events if profile is not None else 0
        variance = 1.0 / (1.0 + n_events)

        return EngineOutput(
            score=score,
            variance=variance,
            explanation=f"ECOD percentile {score:.1f} vs. baseline population",
        )
