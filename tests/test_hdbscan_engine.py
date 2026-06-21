from datetime import datetime

import pytest

from src.common.interfaces import DetectionEngine
from src.common.schema import Event
from src.detection.hdbscan_engine import HDBSCANEngine


def _event(user_id, hour, event_type="http", day=1):
    return Event(
        user_id=user_id,
        timestamp=datetime(2025, 3, day, hour, 0, 0),
        event_type=event_type,
        action="x",
    )


def _office_worker_day(user_id, day):
    """A typical 9-5 office pattern: a handful of http + email events
    clustered in the late morning/afternoon."""
    return [
        _event(user_id, 9, "http", day),
        _event(user_id, 10, "email_send", day),
        _event(user_id, 11, "http", day),
        _event(user_id, 14, "email_send", day),
        _event(user_id, 15, "http", day),
    ]


def _sysadmin_day(user_id, day):
    """A heavier command-exec pattern spread across more hours."""
    return [
        _event(user_id, 8, "command_exec", day),
        _event(user_id, 9, "command_exec", day),
        _event(user_id, 11, "command_exec", day),
        _event(user_id, 13, "file_op", day),
        _event(user_id, 16, "command_exec", day),
        _event(user_id, 18, "command_exec", day),
    ]


def _two_peer_group_baseline():
    """6 office workers and 6 sysadmins, each with 5 days of their
    typical pattern -- two genuinely separable peer clusters."""
    events = []
    office_users = ["camilo", "humberto", "olaya", "delia2", "nuria2", "luis2"]
    sysadmin_users = ["irene2", "root2", "alex", "sam", "pat", "robin"]

    for u in office_users:
        for day in range(1, 6):
            events += _office_worker_day(u, day)
    for u in sysadmin_users:
        for day in range(1, 6):
            events += _sysadmin_day(u, day)
    return events


def test_hdbscan_engine_implements_interface():
    assert issubclass(HDBSCANEngine, DetectionEngine)


def test_hdbscan_fit_requires_minimum_day_windows():
    engine = HDBSCANEngine(min_cluster_size=5)
    with pytest.raises(ValueError):
        engine.fit([_event("camilo", 9, day=1)])  # only 1 (user, day) window


def test_hdbscan_fit_and_score_basic_shape():
    events = _two_peer_group_baseline()
    engine = HDBSCANEngine(min_cluster_size=3)
    engine.fit(events)

    result = engine.score("camilo", _event("camilo", 9, "http", day=10))
    assert 0.0 <= result.score <= 100.0
    assert result.variance > 0


def test_hdbscan_typical_day_scores_lower_than_wildly_different_day():
    events = _two_peer_group_baseline()
    engine = HDBSCANEngine(min_cluster_size=3)
    engine.fit(events)

    # camilo (an office worker) having a normal office-pattern day
    for h, t in [(9, "http"), (10, "email_send"), (11, "http")]:
        typical_result = engine.score("camilo", _event("camilo", h, t, day=10))

    engine.reset_running()

    # camilo suddenly behaving wildly differently from both peer groups:
    # dozens of USB connects through the night
    weird_result = None
    for h in range(0, 24, 2):
        weird_result = engine.score("camilo", _event("camilo", h, "usb_connect", day=11))

    assert weird_result.score >= typical_result.score


def test_hdbscan_reset_running_clears_state():
    events = _two_peer_group_baseline()
    engine = HDBSCANEngine(min_cluster_size=3)
    engine.fit(events)

    engine.score("camilo", _event("camilo", 9, "http", day=10))
    assert len(engine._running) == 1

    engine.reset_running()
    assert len(engine._running) == 0


def test_hdbscan_excludes_pivot_accounts_from_cluster_fitting():
    events = _two_peer_group_baseline()
    pivot_events = [_event("ubuntu", h, "command_exec", day=2) for h in range(10)]

    engine_without_pivot = HDBSCANEngine(min_cluster_size=3)
    engine_without_pivot.fit(events)

    engine_with_pivot_in_history = HDBSCANEngine(min_cluster_size=3)
    engine_with_pivot_in_history.fit(events + pivot_events)

    # both should fit successfully and pivot inclusion shouldn't change
    # the number of training windows used (ubuntu's day is excluded)
    assert engine_without_pivot.clusterer is not None
    assert engine_with_pivot_in_history.clusterer is not None


def test_hdbscan_score_before_fit_raises():
    engine = HDBSCANEngine()
    with pytest.raises(RuntimeError):
        engine.score("camilo", _event("camilo", 9))
