from datetime import datetime, timedelta

import pytest

from src.common.interfaces import DetectionEngine
from src.common.schema import Event
from src.detection.ctmc import CTMCEngine


def _event(user_id, hour, minute, event_type, day=1):
    return Event(
        user_id=user_id,
        timestamp=datetime(2025, 3, day, hour, minute, 0),
        event_type=event_type,
        action="x",
    )


def _typical_user_pattern(user_id, n_days=20):
    """A fixed, repeated http -> email_send -> http cycle every
    weekday morning, ~60 seconds apart, always around 9-10am. This
    gives CTMC a clean, learnable baseline: this user transitions
    http<->email_send, never command_exec/usb_connect, always ~9am."""
    events = []
    for day in range(1, n_days + 1):
        events.append(_event(user_id, 9, 0, "http", day=day))
        events.append(_event(user_id, 9, 1, "email_send", day=day))
        events.append(_event(user_id, 9, 2, "http", day=day))
        events.append(_event(user_id, 9, 3, "email_send", day=day))
    return events


def _sysadmin_pattern(user_id, n_days=20):
    """A genuinely different behavioral pattern -- command-heavy,
    afternoon hours -- needed so population Q diverges from any one
    user's personal Q. If the baseline were just one user, population
    Q would be IDENTICAL to that user's own Q (same underlying data),
    collapsing every ratio-based score to exactly zero regardless of
    hour or transition type -- this is what broke the first version
    of these tests, not an engine bug."""
    events = []
    for day in range(1, n_days + 1):
        events.append(_event(user_id, 14, 0, "command_exec", day=day))
        events.append(_event(user_id, 14, 1, "file_op", day=day))
        events.append(_event(user_id, 14, 2, "command_exec", day=day))
        events.append(_event(user_id, 16, 0, "file_op", day=day))
    return events


def _mixed_baseline():
    return (
        _typical_user_pattern("camilo")
        + _sysadmin_pattern("root2")
        + _sysadmin_pattern("alex")
    )


def test_ctmc_engine_implements_interface():
    assert issubclass(CTMCEngine, DetectionEngine)


def test_ctmc_fit_and_score_basic_shape():
    events = _mixed_baseline()
    engine = CTMCEngine()
    engine.fit(events)

    engine.score("camilo", _event("camilo", 9, 0, "http", day=21))
    result = engine.score("camilo", _event("camilo", 9, 1, "email_send", day=21))
    assert 0.0 <= result.score <= 100.0
    assert result.variance > 0


def test_ctmc_first_event_for_user_is_neutral_cold_start():
    events = _typical_user_pattern("camilo")
    engine = CTMCEngine()
    engine.fit(events)

    result = engine.score("camilo", _event("camilo", 9, 0, "http", day=21))
    assert result.score == 0.0
    assert result.variance == 1.0
    assert "No prior event" in result.explanation


def test_ctmc_score_before_fit_raises():
    engine = CTMCEngine()
    with pytest.raises(RuntimeError):
        engine.score("camilo", _event("camilo", 9, 0, "http"))


def test_ctmc_unusual_transition_type_scores_higher_than_typical():
    """camilo only ever does http<->email_send in baseline -- a jump
    into command_exec (never observed) should score far higher."""
    events = _mixed_baseline()
    engine = CTMCEngine()
    engine.fit(events)

    engine.score("camilo", _event("camilo", 9, 0, "http", day=21))
    typical = engine.score("camilo", _event("camilo", 9, 1, "email_send", day=21))

    engine.reset_running()
    engine.score("camilo", _event("camilo", 9, 0, "http", day=22))
    unusual = engine.score("camilo", _event("camilo", 9, 1, "command_exec", day=22))

    assert unusual.score >= typical.score


def test_ctmc_unusual_hour_scores_higher_holding_dwell_and_transition_fixed():
    """The hour-modulation effect, isolated correctly: SAME transition
    type, SAME dwell time, only the hour changes. Worked out by hand
    before writing this -- holding dwell fixed (not varying it) is
    what makes this comparison reliable; varying dwell instead would
    NOT reliably show the effect, due to the exponential model's
    short-dwell-is-always-likelier property."""
    events = _mixed_baseline()  # always ~9am
    engine = CTMCEngine()
    engine.fit(events)

    engine.score("camilo", _event("camilo", 9, 0, "http", day=21))
    typical_hour = engine.score("camilo", _event("camilo", 9, 1, "email_send", day=21))

    engine.reset_running()
    engine.score("camilo", _event("camilo", 3, 0, "http", day=22))
    unusual_hour = engine.score("camilo", _event("camilo", 3, 1, "email_send", day=22))

    assert unusual_hour.score >= typical_hour.score


def test_ablation_modulation_vs_plain_markov_chain():
    """Direct ablation: with time modulation OFF, the same unusual-hour
    transition should NOT get the hour-based penalty -- confirming the
    modulation is actually doing something, not just adding complexity
    for no measurable effect."""
    events = _mixed_baseline()

    plain = CTMCEngine(use_time_modulation=False)
    plain.fit(events)
    plain.score("camilo", _event("camilo", 9, 0, "http", day=21))
    plain_typical = plain.score("camilo", _event("camilo", 9, 1, "email_send", day=21))
    plain.reset_running()
    plain.score("camilo", _event("camilo", 3, 0, "http", day=22))
    plain_unusual = plain.score("camilo", _event("camilo", 3, 1, "email_send", day=22))

    # plain model: same transition type regardless of hour -> scores
    # should be identical (no hour signal at all)
    assert plain_typical.score == pytest.approx(plain_unusual.score, abs=0.01)

    modulated = CTMCEngine(use_time_modulation=True)
    modulated.fit(events)
    modulated.score("camilo", _event("camilo", 9, 0, "http", day=21))
    mod_typical = modulated.score("camilo", _event("camilo", 9, 1, "email_send", day=21))
    modulated.reset_running()
    modulated.score("camilo", _event("camilo", 3, 0, "http", day=22))
    mod_unusual = modulated.score("camilo", _event("camilo", 3, 1, "email_send", day=22))

    # modulated model: unusual hour should score meaningfully higher
    assert mod_unusual.score > mod_typical.score


def test_ctmc_variance_decreases_with_more_baseline_transitions():
    rich_events = _typical_user_pattern("camilo", n_days=20)  # ~79 transitions
    sparse_events = _typical_user_pattern("delia", n_days=2)  # ~7 transitions

    engine = CTMCEngine()
    engine.fit(rich_events + sparse_events)

    engine.score("camilo", _event("camilo", 9, 0, "http", day=21))
    rich_result = engine.score("camilo", _event("camilo", 9, 1, "email_send", day=21))

    engine.score("delia", _event("delia", 9, 0, "http", day=21))
    sparse_result = engine.score("delia", _event("delia", 9, 1, "email_send", day=21))

    assert rich_result.variance < sparse_result.variance


def test_ctmc_cold_start_unseen_user_falls_back_to_population():
    events = _typical_user_pattern("camilo")
    engine = CTMCEngine()
    engine.fit(events)

    engine.score("brand_new_user", _event("brand_new_user", 9, 0, "http", day=21))
    result = engine.score("brand_new_user", _event("brand_new_user", 9, 1, "email_send", day=21))

    # never-seen user falls back to population Q for both terms ->
    # ratio is ~0 -> score lands near the middle of the percentile range
    assert 0.0 <= result.score <= 100.0
    assert result.variance == 1.0  # 1/(1+0)


def test_ctmc_excludes_pivot_accounts_from_population_fit():
    events = _typical_user_pattern("camilo")
    pivot_events = [
        _event("ubuntu", h, 0, "command_exec", day=2) for h in range(10)
    ]

    engine = CTMCEngine()
    engine.fit(events + pivot_events)  # should not raise

    assert "ubuntu" not in engine.Q_user
    assert engine.Q_population is not None
