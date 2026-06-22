"""
Offline rule mining and validation against SPEDIA's Anomaly label.

This is research/validation code, not part of the deployed pipeline --
it's deliberately the only place in the repo that looks at Event
together with the Anomaly label at the same time (see
src.ingest.spedia.load_spedia's docstring on why the deployed engines
never get that combination).

Run evaluate_all() against the real dataset, look at precision/recall/
support per candidate, and only rules that clear your precision bar
graduate into src/detection/rules.py as deployed checks.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional

import pandas as pd

from src.common.schema import Event
from src.ingest.spedia import PIVOT_ACCOUNTS

PRIVESC_KEYWORDS = ("sudo", "chmod 777", "/etc/shadow", "/etc/passwd", "nc -", "wget ", "curl ")


@dataclass
class RuleCandidate:
    name: str
    predicate: Callable[[Event], bool]


@dataclass
class RuleEvalResult:
    name: str
    support: int  # how many events the rule fired on
    precision: float  # of those, fraction actually labeled anomalous
    recall: float  # of all anomalous events, fraction this rule caught


def _safe_str(value: object) -> str:
    """None and pandas NaN (a float) both mean 'no value' here, but
    NaN is truthy in Python -- `value or ""` alone does NOT catch it,
    which is exactly the bug this function exists to prevent."""
    if value is None or isinstance(value, float):
        return ""
    return str(value)


def _is_pivot_account(e: Event) -> bool:
    return e.user_id in PIVOT_ACCOUNTS


def _description_highly_suspicious(e: Event) -> bool:
    desc = _safe_str((e.raw or {}).get("Description"))
    return "Highly Suspicious" in desc


def _description_any_suspicious(e: Event) -> bool:
    desc = _safe_str((e.raw or {}).get("Description"))
    return any(tag in desc for tag in ("Highly Suspicious", "Midly Suspicious", "Suspicious"))


def _level_at_least(threshold: float) -> Callable[[Event], bool]:
    def check(e: Event) -> bool:
        level = (e.raw or {}).get("Level")
        try:
            return level is not None and float(level) >= threshold
        except (TypeError, ValueError):
            return False

    return check


def _command_privesc_keyword(e: Event) -> bool:
    cmd = (e.raw or {}).get("Command")
    if cmd is None or isinstance(cmd, float):  # NaN from pandas is a float
        return False
    cmd = str(cmd).lower()
    return any(kw in cmd for kw in PRIVESC_KEYWORDS)


DEFAULT_CANDIDATES: List[RuleCandidate] = [
    RuleCandidate("is_pivot_account", _is_pivot_account),
    RuleCandidate("description_highly_suspicious", _description_highly_suspicious),
    RuleCandidate("description_any_suspicious", _description_any_suspicious),
    RuleCandidate("level_at_least_7", _level_at_least(7)),
    RuleCandidate("level_at_least_9", _level_at_least(9)),
    RuleCandidate("command_privesc_keyword", _command_privesc_keyword),
]


def evaluate_rule(
    candidate: RuleCandidate,
    events: List[Event],
    labels: pd.DataFrame,
) -> RuleEvalResult:
    """labels must be the same length and row order as events -- exactly
    what load_spedia() returns. Position is used for alignment, not the
    DataFrame's index, so this works regardless of how labels was sliced."""
    anomaly = labels["anomaly"].tolist()
    fired = [candidate.predicate(e) for e in events]

    fired_count = sum(fired)
    true_positive = sum(1 for f, a in zip(fired, anomaly) if f and a == 1)
    total_anomalous = sum(anomaly)

    precision = true_positive / fired_count if fired_count > 0 else 0.0
    recall = true_positive / total_anomalous if total_anomalous > 0 else 0.0

    return RuleEvalResult(name=candidate.name, support=fired_count, precision=precision, recall=recall)


def evaluate_all(
    events: List[Event],
    labels: pd.DataFrame,
    candidates: Optional[List[RuleCandidate]] = None,
) -> pd.DataFrame:
    """Returns a DataFrame sorted by precision, descending -- the
    rules most worth deploying float to the top."""
    candidates = candidates if candidates is not None else DEFAULT_CANDIDATES
    rows = [evaluate_rule(c, events, labels) for c in candidates]
    return pd.DataFrame([r.__dict__ for r in rows]).sort_values("precision", ascending=False)
