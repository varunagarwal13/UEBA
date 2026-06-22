"""
Deterministic rule engine -- the first deployed detection engine.

Each rule's predicate logic mirrors a candidate from
src/eval/rule_mining.py. That module is the only place allowed to look
at Event + the Anomaly label together; THIS class only ever sees
Event, at both fit() and score() time -- there's no label access path
here at all.

fit() doesn't learn anything statistical for these rules -- they're
fixed thresholds chosen during offline mining, not per-user baselines.
If you add a rule that DOES need a per-user baseline (e.g. "more
commands today than this user's normal day"), wire it through
src.profile.build rather than computing it inline here.

IMPORTANT: the `precision` values on DEFAULT_RULES below are
placeholders, not measured numbers -- this engine was built before
rule_mining.py had been run against the real 72k-row dataset. Run
`python -m src.eval.rule_mining` (or the equivalent in a notebook)
against logs_SPEDIA_annotated_en.csv, then update DEFAULT_RULES'
`score` and `precision` fields -- and drop any rule that doesn't clear
your precision bar -- before trusting this for anything beyond local
testing against the fixture.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional

from src.common.interfaces import DetectionEngine
from src.common.schema import Event, EngineOutput
from src.ingest.spedia import PIVOT_ACCOUNTS

PRIVESC_KEYWORDS = ("sudo", "chmod 777", "/etc/shadow", "/etc/passwd", "nc -", "wget ", "curl ")


@dataclass
class Rule:
    name: str
    predicate: Callable[[Event], bool]
    score: float  # risk score (0-100) this rule contributes if it fires
    precision: float  # measured precision from rule_mining.py -- drives variance


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
    if cmd is None or isinstance(cmd, float):
        return False
    cmd = str(cmd).lower()
    return any(kw in cmd for kw in PRIVESC_KEYWORDS)


# PLACEHOLDER precision/score values -- see module docstring. Replace
# with real numbers from rule_mining.py before deploying past local tests.
DEFAULT_RULES: List[Rule] = [
    Rule("is_pivot_account", _is_pivot_account, score=95.0, precision=0.95),
    Rule("description_highly_suspicious", _description_highly_suspicious, score=90.0, precision=0.95),
    Rule("level_at_least_9", _level_at_least(9), score=80.0, precision=0.90),
    Rule("command_privesc_keyword", _command_privesc_keyword, score=85.0, precision=0.90),
]


class RuleEngine(DetectionEngine):
    def __init__(self, rules: Optional[List[Rule]] = None):
        self.rules = rules if rules is not None else DEFAULT_RULES

    def fit(self, history: List[Event]) -> None:
        # Fixed thresholds from offline mining -- nothing statistical
        # to learn per-user at fit time for the current rule set.
        pass

    def score(self, user_id: str, event: Event) -> EngineOutput:
        fired = [r for r in self.rules if r.predicate(event)]
        if not fired:
            # No rule caught this -- not "definitely benign", just
            # "this limited rule set didn't catch anything". Higher
            # variance than a fired rule reflects that lower confidence.
            return EngineOutput(score=0.0, variance=1.0, explanation=None)

        best = max(fired, key=lambda r: r.score)
        variance = max(1.0 - best.precision, 0.01)
        names = ", ".join(r.name for r in fired)
        return EngineOutput(
            score=best.score,
            variance=variance,
            explanation=f"Rule(s) fired: {names}",
        )
