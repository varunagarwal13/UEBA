import math
from datetime import datetime

from src.common.schema import Event
from src.eval.rule_mining import (
    DEFAULT_CANDIDATES,
    _description_any_suspicious,
    _description_highly_suspicious,
    evaluate_all,
    evaluate_rule,
)
from src.ingest.spedia import load_spedia


def _load_fixture():
    return load_spedia("tests/fixtures/sample_spedia.csv")


def test_is_pivot_account_rule_against_fixture():
    events, labels = _load_fixture()
    result = evaluate_rule(DEFAULT_CANDIDATES[0], events, labels)  # is_pivot_account

    # only ubuntu (a4) is a pivot account in the fixture, and it's anomalous
    assert result.support == 1
    assert result.precision == 1.0
    # 2 anomalous rows total (irene a3, ubuntu a4) -- this rule catches 1
    assert result.recall == 0.5


def test_level_at_least_9_against_fixture():
    events, labels = _load_fixture()
    candidate = next(c for c in DEFAULT_CANDIDATES if c.name == "level_at_least_9")
    result = evaluate_rule(candidate, events, labels)

    # irene (level 9, anomaly=1) and ubuntu (level 9, anomaly=1) fire;
    # camilo's systemctl row (level 8) does not
    assert result.support == 2
    assert result.precision == 1.0
    assert result.recall == 1.0


def test_level_at_least_7_catches_a_false_positive():
    events, labels = _load_fixture()
    candidate = next(c for c in DEFAULT_CANDIDATES if c.name == "level_at_least_7")
    result = evaluate_rule(candidate, events, labels)

    # camilo's systemctl row (level 8, anomaly=0) now also fires,
    # alongside irene and ubuntu (both level 9, anomaly=1)
    assert result.support == 3
    assert result.precision == 2 / 3
    assert result.recall == 1.0


def test_command_privesc_keyword_against_fixture():
    events, labels = _load_fixture()
    candidate = next(c for c in DEFAULT_CANDIDATES if c.name == "command_privesc_keyword")
    result = evaluate_rule(candidate, events, labels)

    # only ubuntu's "cat /etc/shadow" matches a privesc keyword
    assert result.support == 1
    assert result.precision == 1.0
    assert result.recall == 0.5


def test_evaluate_all_returns_sorted_by_precision():
    events, labels = _load_fixture()
    df = evaluate_all(events, labels)

    assert list(df.columns) == ["name", "support", "precision", "recall"]
    # sorted descending -- first row's precision is the max across all candidates
    assert df.iloc[0]["precision"] >= df.iloc[-1]["precision"]


def test_description_rules_survive_nan_description():
    """Regression test: pandas NaN is a float and floats are truthy in
    Python, so `value or ""` does NOT catch NaN the way it catches None.
    ~86% of real SPEDIA rows have NaN Description -- this crashed on
    the very first NaN row before the fix."""
    nan_event = Event(
        user_id="camilo", timestamp=datetime(2025, 3, 6), event_type="http",
        action="x", raw={"Description": math.nan},
    )
    assert _description_highly_suspicious(nan_event) is False
    assert _description_any_suspicious(nan_event) is False

    none_event = Event(
        user_id="camilo", timestamp=datetime(2025, 3, 6), event_type="http",
        action="x", raw={},
    )
    assert _description_highly_suspicious(none_event) is False
