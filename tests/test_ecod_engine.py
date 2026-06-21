from datetime import datetime

import pytest

from src.common.interfaces import DetectionEngine
from src.common.schema import Event
from src.detection.ecod import ECODEngine


def _event(user_id, hour, event_type="http", resource=None, command=None, day=6):
    return Event(
        user_id=user_id,
        timestamp=datetime(2025, 3, day, hour, 0, 0),
        event_type=event_type,
        action="x",
        resource=resource,
        raw={"Command": command} if command else None,
    )


def _camilo_typical_baseline():
    """camilo's normal pattern: weekday-ish hours, http + email, same resources."""
    events = []
    for day in range(1, 15):
        events.append(_event("camilo", 9 + (day % 6), event_type="http", resource="intranet", day=day))
        events.append(_event("camilo", 10 + (day % 5), event_type="email_send", resource="team@x.com", day=day))
    return events


def test_ecod_engine_implements_interface():
    assert issubclass(ECODEngine, DetectionEngine)


def test_ecod_fit_and_score_basic_shape():
    events = _camilo_typical_baseline()
    engine = ECODEngine()
    engine.fit(events)

    result = engine.score("camilo", _event("camilo", 10, event_type="http", resource="intranet", day=20))
    assert 0.0 <= result.score <= 100.0
    assert result.variance > 0


def test_ecod_flags_unusual_hour_higher_than_typical_hour():
    events = _camilo_typical_baseline()
    engine = ECODEngine()
    engine.fit(events)

    typical = engine.score("camilo", _event("camilo", 10, event_type="http", resource="intranet", day=20))
    unusual = engine.score("camilo", _event("camilo", 3, event_type="http", resource="intranet", day=20))

    assert unusual.score >= typical.score


def test_ecod_flags_unusual_resource_higher_than_typical_resource():
    events = _camilo_typical_baseline()
    engine = ECODEngine()
    engine.fit(events)

    typical = engine.score("camilo", _event("camilo", 10, event_type="http", resource="intranet", day=20))
    unusual = engine.score(
        "camilo", _event("camilo", 10, event_type="file_op", resource="/etc/shadow", day=20)
    )

    assert unusual.score >= typical.score


def test_ecod_cold_start_unseen_user_does_not_crash():
    events = _camilo_typical_baseline()
    engine = ECODEngine()
    engine.fit(events)

    result = engine.score("brand_new_user", _event("brand_new_user", 10))
    assert 0.0 <= result.score <= 100.0
    assert result.variance == 1.0  # n_events=0 -> 1/(1+0)


def test_ecod_excludes_pivot_accounts_from_training():
    camilo_events = _camilo_typical_baseline()
    ubuntu_event = _event("ubuntu", 3, event_type="command_exec", command="cat /etc/shadow", day=10)

    engine = ECODEngine()
    engine.fit(camilo_events + [ubuntu_event])

    assert len(engine._train_scores) == len(camilo_events)


def test_ecod_fit_raises_if_no_usable_training_events():
    engine = ECODEngine()
    only_pivot = [_event("ubuntu", 9)]

    with pytest.raises(ValueError):
        engine.fit(only_pivot)


def test_ecod_score_before_fit_raises():
    engine = ECODEngine()
    with pytest.raises(RuntimeError):
        engine.score("camilo", _event("camilo", 9))
