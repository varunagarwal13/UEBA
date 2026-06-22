from src.detection.rules import RuleEngine
from src.ingest.spedia import load_spedia


def test_rule_engine_fires_on_pivot_account_event():
    events, _ = load_spedia("tests/fixtures/sample_spedia.csv")
    engine = RuleEngine()
    engine.fit(events)

    ubuntu_event = next(e for e in events if e.user_id == "ubuntu")
    result = engine.score("ubuntu", ubuntu_event)

    assert result.score > 0
    assert "is_pivot_account" in result.explanation


def test_rule_engine_no_score_when_nothing_fires():
    events, _ = load_spedia("tests/fixtures/sample_spedia.csv")
    engine = RuleEngine()
    engine.fit(events)

    # humberto's plain login shouldn't trip any default rule
    humberto_event = next(e for e in events if e.user_id == "humberto")
    result = engine.score("humberto", humberto_event)

    assert result.score == 0.0
    assert result.explanation is None


def test_rule_engine_picks_highest_scoring_rule_when_multiple_fire():
    events, _ = load_spedia("tests/fixtures/sample_spedia.csv")
    engine = RuleEngine()
    engine.fit(events)

    # ubuntu's event is both a pivot account (95) AND has a privesc
    # command (85) AND level >= 9 (80) -- should report the highest, 95
    ubuntu_event = next(e for e in events if e.user_id == "ubuntu")
    result = engine.score("ubuntu", ubuntu_event)

    assert result.score == 95.0


def test_engine_implements_detection_engine_interface():
    from src.common.interfaces import DetectionEngine

    assert issubclass(RuleEngine, DetectionEngine)


def test_rule_engine_survives_nan_description():
    """Regression test: most real SPEDIA rows have NaN (not None) in
    Description, which is a float and therefore truthy -- 'value or ""'
    doesn't catch it. This crashed on the real dataset before the fix
    in _description_highly_suspicious."""
    import math
    from datetime import datetime

    from src.common.schema import Event

    engine = RuleEngine()
    engine.fit([])  # rules are fixed thresholds, fit() is a no-op

    nan_desc_event = Event(
        user_id="camilo", timestamp=datetime(2025, 3, 6), event_type="http",
        action="x", raw={"Description": math.nan, "Level": math.nan, "Command": math.nan},
    )
    result = engine.score("camilo", nan_desc_event)  # must not raise
    assert result.score == 0.0
