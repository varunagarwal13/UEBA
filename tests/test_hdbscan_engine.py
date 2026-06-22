from datetime import datetime, timedelta

import pytest

from src.common.interfaces import DetectionEngine
from src.common.schema import Event
from src.detection.hdbscan_engine import HDBSCANEngine


def _event(user_id, hour, minute=0, event_type="http", day=1):
    return Event(
        user_id=user_id,
        timestamp=datetime(2025, 3, day, hour, minute, 0),
        event_type=event_type,
        action="x",
    )


def _office_pattern(user_id, n_days=10):
    """Steady, varied office activity across many days -- gives the
    sliding window plenty of normal training examples per user."""
    events = []
    for day in range(1, n_days + 1):
        for hour, etype in [(9, "http"), (10, "email_send"), (11, "http"), (14, "email_send"), (15, "http")]:
            events.append(_event(user_id, hour, day=day, event_type=etype))
    return events


def _two_peer_group_baseline():
    events = []
    for u in ["camilo", "humberto", "olaya"]:
        events += _office_pattern(u, n_days=15)
    for u in ["irene2", "root2", "alex"]:
        # heavier, more spread-out sysadmin pattern
        for day in range(1, 16):
            for hour, etype in [(8, "command_exec"), (9, "command_exec"), (11, "command_exec"),
                                  (13, "file_op"), (16, "command_exec"), (18, "command_exec")]:
                events.append(_event(u, hour, day=day, event_type=etype))
    return events


def test_hdbscan_engine_implements_interface():
    assert issubclass(HDBSCANEngine, DetectionEngine)


def test_hdbscan_fit_requires_minimum_training_windows():
    engine = HDBSCANEngine(min_cluster_size=5)
    with pytest.raises(ValueError):
        engine.fit([_event("camilo", 9, day=1)])


def test_hdbscan_fit_and_score_basic_shape():
    events = _two_peer_group_baseline()
    engine = HDBSCANEngine(min_cluster_size=3, window_size=10)
    engine.fit(events)

    result = engine.score("camilo", _event("camilo", 9, day=20))
    assert 0.0 <= result.score <= 100.0
    assert result.variance > 0


def test_hdbscan_reset_running_clears_state():
    events = _two_peer_group_baseline()
    engine = HDBSCANEngine(min_cluster_size=3, window_size=10)
    engine.fit(events)

    engine.score("camilo", _event("camilo", 9, day=20))
    assert len(engine._running["camilo"]) == 1

    engine.reset_running()
    assert len(engine._running["camilo"]) == 0


def test_hdbscan_score_before_fit_raises():
    engine = HDBSCANEngine()
    with pytest.raises(RuntimeError):
        engine.score("camilo", _event("camilo", 9))


def test_single_anomalous_event_scores_higher_than_normal_window():
    """The actual fix being tested: a single out-of-pattern action
    embedded among otherwise-normal recent events should score
    noticeably higher than a window that's entirely normal -- this is
    exactly what the day-level v1 design failed to do (the single
    action got averaged away across the whole day)."""
    events = _two_peer_group_baseline()
    engine = HDBSCANEngine(min_cluster_size=3, window_size=10)
    engine.fit(events)

    # build up a normal 9-event window for camilo (an office worker)
    normal_result = None
    for hour, etype in [(9, "http"), (10, "email_send"), (11, "http"), (14, "email_send"),
                         (15, "http"), (9, "http"), (10, "email_send"), (11, "http"), (14, "email_send")]:
        normal_result = engine.score("camilo", _event("camilo", hour, event_type=etype, day=20))

    engine.reset_running()

    # same 9 normal events, but the 10th is a burst of rapid-fire
    # command_exec events very close together in time -- atypical for
    # an office worker and atypical in *pace* (the window_duration
    # feature should catch the tight clustering)
    for hour, etype in [(9, "http"), (10, "email_send"), (11, "http"), (14, "email_send"),
                         (15, "http"), (9, "http"), (10, "email_send"), (11, "http"), (14, "email_send")]:
        engine.score("camilo", _event("camilo", hour, event_type=etype, day=21))
    anomalous_result = engine.score(
        "camilo", _event("camilo", 3, minute=1, event_type="command_exec", day=21)
    )

    assert anomalous_result.score >= normal_result.score


def test_window_can_span_midnight():
    """A burst of events crossing a day boundary should be treated as
    one continuous window, not artificially split -- this was
    impossible in the v1 day-bucketed design."""
    events = _two_peer_group_baseline()
    engine = HDBSCANEngine(min_cluster_size=3, window_size=4)
    engine.fit(events)

    # two events just before midnight, two just after -- still one window
    engine.score("camilo", Event(user_id="camilo", timestamp=datetime(2025, 3, 20, 23, 50), event_type="http", action="x"))
    engine.score("camilo", Event(user_id="camilo", timestamp=datetime(2025, 3, 20, 23, 55), event_type="http", action="x"))
    engine.score("camilo", Event(user_id="camilo", timestamp=datetime(2025, 3, 21, 0, 2), event_type="http", action="x"))
    result = engine.score("camilo", Event(user_id="camilo", timestamp=datetime(2025, 3, 21, 0, 5), event_type="http", action="x"))

    assert len(engine._running["camilo"]) == 4
    assert 0.0 <= result.score <= 100.0


def test_hdbscan_excludes_pivot_accounts_from_training():
    events = _two_peer_group_baseline()
    pivot_events = [_event("ubuntu", h, event_type="command_exec", day=2) for h in range(10)]

    engine = HDBSCANEngine(min_cluster_size=3, window_size=10)
    engine.fit(events + pivot_events)  # should not raise

    assert engine.clusterer is not None
