"""
Canonical data contracts for the UEBA pipeline.

Everyone on the team imports from here instead of inventing their own
event dict shape or score format. If this file changes, it's a team
conversation, not a solo decision in someone's branch.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    """One row of normalized activity, derived from a raw SPEDIA log line."""

    user_id: str
    timestamp: datetime
    event_type: str  # login | logout | command_exec | file_op | http | email | usb_connect
    action: str  # e.g. "create", "delete", "send", "connect", specific command name
    resource: Optional[str] = None  # file path, URL, recipient, device id, etc.
    raw: Optional[dict] = None  # original SPEDIA fields, kept for debugging/XAI


@dataclass
class EngineOutput:
    """What every detection engine must return for a single (user, event) pair."""

    score: float  # calibrated risk score, 0-100, higher = more anomalous
    variance: float  # sigma^2 — how much to trust this score. Lower = more confident.
    explanation: Optional[str] = None  # short human-readable reason, for XAI layer
