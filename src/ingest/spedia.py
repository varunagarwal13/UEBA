"""
Normalize logs_SPEDIA_annotated_en.csv into the canonical Event schema
every engine consumes.

Two design decisions here come straight out of EDA, not guesswork:

1. Ground truth (`Anomaly`) is deliberately kept OUT of Event and
   Event.raw. It lives only in the separate `labels` table returned
   alongside `events`, joined by `id`. Only src/eval/ should ever
   import the labels table. This is the cheapest possible defense
   against an engine accidentally "detecting" its own label.

2. PIVOT_ACCOUNTS and the baseline/campaign split both encode a real
   finding: every account in PIVOT_ACCOUNTS has ZERO benign rows
   anywhere in the dataset -- they're attacker-controlled escalation
   infrastructure, not real day-to-day personas, so there's no
   legitimate baseline to profile them against. Separately, every
   user except irene/ubuntu has zero anomalous activity before
   2025-03-23 -- the attack narrative is concentrated in a campaign
   phase, not spread evenly across the 30 days.
"""

from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd

from src.common.schema import Event

# Accounts that show zero benign activity whenever they appear in the
# data -- attacker-controlled pivot/escalation infrastructure, not
# real personas. Exclude these from per-user profiling (ECOD/CTMC/
# HDBSCAN "what's normal for this user") since no normal exists for
# them to deviate from.
PIVOT_ACCOUNTS = frozenset({
    "ubuntu", "ubuntu(uid=1000)", "wazuh", "wazuh(uid=129)",
    "gdm", "gdm(uid=128)", "delia", "nuria", "impresora",
})

# Decoder_name == 'cert' rows are synthetic background events injected
# directly from the CERT dataset -- no live Wazuh rule ever evaluated
# them. Useful as a confidently-clean reference population.
SYNTHETIC_DECODER = "cert"

# Every user except irene/ubuntu has zero anomalous activity before
# this date. Use it to fit baselines on the quiet period and evaluate
# detection (including time-to-detect) over the campaign period,
# instead of a naive random or chronological split that would badly
# distort train/test base rates.
DEFAULT_CAMPAIGN_START = "2025-03-23"


def _first_present(*values) -> "str | None":
    for v in values:
        if v is None:
            continue
        if isinstance(v, float) and pd.isna(v):
            continue
        return str(v)
    return None


def _infer_event_type(activity: str, action: str) -> str:
    """Collapse SPEDIA's (Activity, Action) pairs into the canonical
    event_type taxonomy used across all four detection engines."""
    activity = (activity or "").lower()
    action = (action or "").lower()

    if activity == "session":
        if "fail" in action:
            return "login_failed"
        if "login" in action:
            return "login"
        return "logout"
    if activity == "command":
        return "command_exec"
    if activity == "file":
        return "file_op"
    if activity == "http":
        return "http"
    if activity == "email":
        return "email_send"
    if activity == "device":
        return "usb_connect"
    return "unknown"


def load_spedia(path: str) -> Tuple[List[Event], pd.DataFrame]:
    """
    Returns (events, labels).

    events: list[Event] in timestamp order, the canonical stream every
    engine reads. No Anomaly field anywhere in here.

    labels: DataFrame [id, user_id, timestamp, anomaly, is_pivot_account],
    same row order as `events`. Import this in src/eval/ only.
    """
    df = pd.read_csv(path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values("Timestamp").reset_index(drop=True)

    events: List[Event] = []
    for row in df.itertuples(index=False):
        raw = {
            "Agent_name": row.Agent_name,
            "Decoder_name": row.Decoder_name,
            "Description": row.Description,
            "Level": row.Level,
            "Command": row.Command,
            # Anomaly intentionally excluded -- see module docstring
        }
        events.append(
            Event(
                user_id=str(row.User),
                timestamp=row.Timestamp.to_pydatetime(),
                event_type=_infer_event_type(row.Activity, row.Action),
                action=str(row.Action),
                resource=_first_present(row.Filename, row.Path, row.Url, row.To),
                raw=raw,
            )
        )

    labels = pd.DataFrame({
        "id": df["id"],
        "user_id": df["User"].astype(str),
        "timestamp": df["Timestamp"],
        "anomaly": df["Anomaly"],
        "is_pivot_account": df["User"].astype(str).isin(PIVOT_ACCOUNTS),
    })

    return events, labels


def baseline_and_campaign_split(
    labels: pd.DataFrame,
    cutoff: str = DEFAULT_CAMPAIGN_START,
) -> Tuple[pd.Series, pd.Series]:
    """
    Returns (baseline_ids, campaign_ids) -- the `id` values belonging
    to the quiet baseline period vs. the campaign period, split at
    `cutoff`. Use baseline_ids to fit profiles/population stats, and
    campaign_ids to evaluate detection.
    """
    cutoff_ts = pd.Timestamp(cutoff)
    baseline_ids = labels.loc[labels["timestamp"] < cutoff_ts, "id"]
    campaign_ids = labels.loc[labels["timestamp"] >= cutoff_ts, "id"]
    return baseline_ids, campaign_ids
