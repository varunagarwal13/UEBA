"""
Per-user temporal + access profile -- "what's normal for this user".

This is a shared feature-engineering layer. ECOD, HDBSCAN, and CTMC
should import build_profiles() / build_user_profile() inside their own
fit() methods rather than re-deriving these features independently --
that's what keeps "what counts as this user's normal hour" consistent
across all four engines instead of four slightly different answers.

Pass only baseline-period events if you want profiles uncontaminated
by attack behavior -- see src.ingest.spedia.baseline_and_campaign_split.
Every account except irene/ubuntu has zero anomalous activity before
that split point, so baseline-only profiling is a reasonable (not
perfect) approximation of "normal" for everyone else.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.common.schema import Event
from src.ingest.spedia import PIVOT_ACCOUNTS

HOUR_SMOOTHING_ALPHA = 1.0
DOW_SMOOTHING_ALPHA = 1.0


@dataclass
class UserProfile:
    user_id: str
    n_events: int
    hour_of_day_dist: List[float]  # 24 floats, sums to 1.0, Laplace-smoothed
    day_of_week_dist: List[float]  # 7 floats, Mon=0..Sun=6, smoothed
    event_type_counts: Dict[str, int] = field(default_factory=dict)
    access_counts: Dict[str, int] = field(default_factory=dict)  # see _access_key
    inter_event_seconds_mean: Optional[float] = None
    inter_event_seconds_std: Optional[float] = None
    is_pivot_account: bool = False


def _access_key(event: Event) -> Optional[str]:
    """
    What 'thing' did this event touch, for access-pattern profiling.

    Command-exec rows in SPEDIA almost never populate `resource`
    (Filename/Path/Url/To are empty -- the command lives in
    Event.raw['Command'] instead), so command identity is used as the
    access key for those. Everything else uses `resource` directly.
    Returns None when there's nothing to key on (e.g. a login event).
    """
    if event.event_type == "command_exec":
        cmd = (event.raw or {}).get("Command")
        if cmd is None or (isinstance(cmd, float)):  # NaN from pandas is a float
            return None
        return f"cmd:{cmd}"
    if event.resource is not None:
        return f"res:{event.resource}"
    return None


def _smooth(counts: List[int], alpha: float) -> List[float]:
    total = sum(counts)
    n_bins = len(counts)
    denom = total + alpha * n_bins
    return [(c + alpha) / denom for c in counts]


def _inter_event_stats(sorted_events: List[Event]):
    if len(sorted_events) < 2:
        return None, None
    gaps = [
        (b.timestamp - a.timestamp).total_seconds()
        for a, b in zip(sorted_events, sorted_events[1:])
    ]
    mean = sum(gaps) / len(gaps)
    if len(gaps) < 2:
        return mean, None
    variance = sum((g - mean) ** 2 for g in gaps) / len(gaps)
    return mean, variance**0.5


def build_user_profile(user_id: str, events: List[Event]) -> UserProfile:
    """Build one user's profile from their events (already filtered
    to that user -- this function doesn't check user_id against
    event.user_id, see build_profiles() for the grouping version)."""
    events = sorted(events, key=lambda e: e.timestamp)
    n = len(events)

    hour_counts = [0] * 24
    dow_counts = [0] * 7
    event_type_counts: Counter = Counter()
    access_counts: Counter = Counter()

    for e in events:
        hour_counts[e.timestamp.hour] += 1
        dow_counts[e.timestamp.weekday()] += 1
        event_type_counts[e.event_type] += 1
        key = _access_key(e)
        if key is not None:
            access_counts[key] += 1

    inter_mean, inter_std = _inter_event_stats(events)

    return UserProfile(
        user_id=user_id,
        n_events=n,
        hour_of_day_dist=_smooth(hour_counts, HOUR_SMOOTHING_ALPHA),
        day_of_week_dist=_smooth(dow_counts, DOW_SMOOTHING_ALPHA),
        event_type_counts=dict(event_type_counts),
        access_counts=dict(access_counts),
        inter_event_seconds_mean=inter_mean,
        inter_event_seconds_std=inter_std,
        is_pivot_account=user_id in PIVOT_ACCOUNTS,
    )


def build_profiles(events: List[Event]) -> Dict[str, UserProfile]:
    """Group events by user and build a UserProfile for each.

    Profiles are still built for pivot accounts (flagged via
    is_pivot_account=True) rather than silently dropped -- callers
    decide whether to use them as HDBSCAN/ECOD peers, since "every
    action this account takes is anomalous" is itself a legitimate
    reference point, just not a personal baseline to deviate from.
    """
    by_user: Dict[str, List[Event]] = {}
    for e in events:
        by_user.setdefault(e.user_id, []).append(e)

    return {
        user_id: build_user_profile(user_id, user_events)
        for user_id, user_events in by_user.items()
    }


def hour_of_day_likelihood(profile: UserProfile, hour: int) -> float:
    """Probability mass this user is normally active at `hour` (0-23),
    Laplace-smoothed so an unseen hour doesn't collapse a downstream
    log-likelihood to -inf. Used by CTMC's time-of-day modulation."""
    if not 0 <= hour <= 23:
        raise ValueError(f"hour must be 0-23, got {hour}")
    return profile.hour_of_day_dist[hour]
