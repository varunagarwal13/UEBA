"""
Quick evaluation: score the three completed detection engines (rules,
ECOD, HDBSCAN) against the real SPEDIA campaign period, before
investing time in CTMC.

Uses ROC-AUC and PR-AUC -- both rank-based metrics that are unaffected
by calibration (a monotonic transform can't change rank order), so
these numbers stay valid even after the calibration step is built later.

Run with:
    python3 -m src.eval.quick_eval
or paste the contents of main() into a python3 << 'EOF' heredoc.
"""

from typing import List

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from src.common.schema import Event
from src.detection.ecod import ECODEngine
from src.detection.hdbscan_engine import HDBSCANEngine
from src.detection.rules import RuleEngine
from src.eval.rule_mining import evaluate_all
from src.ingest.spedia import PIVOT_ACCOUNTS, baseline_and_campaign_split, load_spedia

DATA_PATH = "data/raw/logs_SPEDIA_annotated_en.csv"


def _events_for_ids(events: List[Event], labels: pd.DataFrame, ids) -> List[Event]:
    """events and labels are guaranteed same-order/same-length by
    load_spedia(), so positional alignment via enumerate is safe."""
    id_set = set(ids)
    keep_idx = [i for i, row_id in enumerate(labels["id"]) if row_id in id_set]
    return [events[i] for i in keep_idx]


def _score_engine(engine, events: List[Event]) -> List[float]:
    return [engine.score(e.user_id, e).score for e in events]


def _report(name: str, y_true, y_score) -> None:
    if len(set(y_true)) < 2:
        print(f"{name}: only one class present in this slice, skipping AUC")
        return
    roc = roc_auc_score(y_true, y_score)
    pr = average_precision_score(y_true, y_score)
    print(f"{name}: ROC-AUC={roc:.3f}  PR-AUC={pr:.3f}  (n={len(y_true)}, positives={sum(y_true)})")


def main():
    print("Loading SPEDIA...")
    events, labels = load_spedia(DATA_PATH)
    baseline_ids, campaign_ids = baseline_and_campaign_split(labels)

    baseline_events = _events_for_ids(events, labels, baseline_ids)
    campaign_events = _events_for_ids(events, labels, campaign_ids)
    campaign_labels = labels[labels["id"].isin(set(campaign_ids))].reset_index(drop=True)

    print(f"\nBaseline: {len(baseline_events)} events | Campaign: {len(campaign_events)} events")

    print("\n=== Rule mining (candidate rules vs. ALL labeled events) ===")
    print(evaluate_all(events, labels).to_string(index=False))

    print("\nFitting engines on baseline period...")
    rule_engine = RuleEngine()
    rule_engine.fit(baseline_events)

    ecod_engine = ECODEngine()
    ecod_engine.fit(baseline_events)

    hdbscan_engine = HDBSCANEngine(min_cluster_size=5)
    hdbscan_engine.fit(baseline_events)

    print("Scoring campaign period (chronological order, matters for HDBSCAN's running state)...")
    rule_scores = _score_engine(rule_engine, campaign_events)
    ecod_scores = _score_engine(ecod_engine, campaign_events)
    hdbscan_engine.reset_running()
    hdbscan_scores = _score_engine(hdbscan_engine, campaign_events)

    y_true = campaign_labels["anomaly"].tolist()
    is_irene_or_ubuntu = [u in ("irene", "ubuntu") for u in campaign_labels["user_id"]]

    print("\n=== Full campaign population ===")
    _report("Rules   ", y_true, rule_scores)
    _report("ECOD    ", y_true, ecod_scores)
    _report("HDBSCAN ", y_true, hdbscan_scores)

    keep = [not f for f in is_irene_or_ubuntu]
    y_true_ex = [v for v, k in zip(y_true, keep) if k]
    print(f"\n=== Excluding irene/ubuntu (n={sum(keep)} of {len(keep)} campaign events) ===")
    _report("Rules   ", y_true_ex, [v for v, k in zip(rule_scores, keep) if k])
    _report("ECOD    ", y_true_ex, [v for v, k in zip(ecod_scores, keep) if k])
    _report("HDBSCAN ", y_true_ex, [v for v, k in zip(hdbscan_scores, keep) if k])

    # Strictest test: zero identity-coded infrastructure at all (every
    # PIVOT_ACCOUNTS member, which are 100% anomalous by construction
    # whenever present -- not just irene/ubuntu) AND irene removed too,
    # since she alone is ~76% of all malicious-labeled rows. What's left
    # is real personas (camilo, humberto, olaya, root, ...) behaving
    # anomalously -- the actual case the product needs to catch.
    is_pivot_or_irene = [
        (u in PIVOT_ACCOUNTS) or (u == "irene") for u in campaign_labels["user_id"]
    ]
    keep_strict = [not f for f in is_pivot_or_irene]
    y_true_strict = [v for v, k in zip(y_true, keep_strict) if k]
    print(f"\n=== Strictest: excluding ALL pivot accounts + irene (n={sum(keep_strict)} of {len(keep_strict)}) ===")
    _report("Rules   ", y_true_strict, [v for v, k in zip(rule_scores, keep_strict) if k])
    _report("ECOD    ", y_true_strict, [v for v, k in zip(ecod_scores, keep_strict) if k])
    _report("HDBSCAN ", y_true_strict, [v for v, k in zip(hdbscan_scores, keep_strict) if k])


if __name__ == "__main__":
    main()
