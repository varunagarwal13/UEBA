# analytics/data/spedia/loader.py
#
# PURPOSE: Load SPEDIA v2 CSV files and convert them into session dicts
#          that match your analytics pipeline's data contract.
#
# INPUT:   Path to SPEDIA_preprocessed.csv
# OUTPUT:  List of session dicts ready for the analytics pipeline
#
# WHY THIS FILE EXISTS:
#   Your analytics pipeline expects sessions in a specific dict format.
#   The SPEDIA data is a flat CSV where every row is one event.
#   This loader bridges that gap: it reads the CSV row by row,
#   groups events into sessions (by user + 30-minute idle gap),
#   and returns them in the format your pipeline understands.

import pandas as pd
from typing import List, Dict, Any


# If a user has been idle for more than this many seconds,
# we consider their next event the start of a NEW session.
# 30 minutes (1800 seconds) is the industry standard for UEBA sessionization.
SESSION_TIMEOUT_SECONDS = 1800


def load_spedia_sessions(csv_path: str) -> List[Dict[str, Any]]:
    """
    Loads SPEDIA_preprocessed.csv and groups events into sessions.

    Parameters:
        csv_path: Full path to SPEDIA_preprocessed.csv
                  Example: "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv"

    Returns:
        List of session dicts. Each looks like:
        {
            "session_id": "SPEDIA_camilo_0001",
            "user_id":    "camilo",
            "anomaly":    1,          <- ground truth: 0=normal, 1=malicious
            "events": [
                {
                    "event_id":     "12089799-...",
                    "user_id":      "camilo",
                    "timestamp":    "2025-03-06T13:15:10Z",
                    "Activity":     "command",
                    "Action":       "Command executed",
                    "Level":        8.0,
                    "Command":      "systemctl",
                    "file_path":    "/etc/apache2/sites-available",
                    "bytes":        0.0,
                    "IsAfterHours": 0,
                    "IsWeekend":    0,
                    "CTMC_State":   "Command",
                    "Anomaly":      0,
                },
                ...
            ]
        }
    """
    print(f"Loading SPEDIA data from: {csv_path}")

    # Read the CSV. parse_dates converts the Timestamp column to datetime objects
    # automatically, which lets us do time arithmetic (subtracting timestamps).
    df = pd.read_csv(csv_path, parse_dates=["Timestamp"], low_memory=False)

    # Sort by User then Timestamp so we process each user's events in order
    df = df.sort_values(["User", "Timestamp"]).reset_index(drop=True)

    print(f"  Total events loaded: {len(df)}")
    print(f"  Unique users: {df['User'].nunique()}")
    print(f"  Anomalous events: {df['Anomaly'].sum()} "
          f"({100*df['Anomaly'].mean():.1f}%)")

    all_sessions = []

    # Process one user at a time
    for user, user_df in df.groupby("User"):

        current_session_events = []
        session_index          = 0
        prev_timestamp         = None

        for _, row in user_df.iterrows():

            current_ts = row["Timestamp"]

            # Decide if this event starts a new session
            # A new session starts when there has been a 30-minute gap
            is_new_session = (
                prev_timestamp is None or
                (current_ts - prev_timestamp).total_seconds() > SESSION_TIMEOUT_SECONDS
            )

            if is_new_session and current_session_events:
                # Save the completed session before starting a new one
                all_sessions.append(
                    _build_session_dict(user, session_index, current_session_events)
                )
                session_index         += 1
                current_session_events = []

            # Convert this CSV row to an event dict
            event = _row_to_event_dict(row)
            current_session_events.append(event)
            prev_timestamp = current_ts

        # Don't forget the last session (loop ends without triggering the save above)
        if current_session_events:
            all_sessions.append(
                _build_session_dict(user, session_index, current_session_events)
            )

    print(f"  Total sessions created: {len(all_sessions)}")
    anomalous = sum(1 for s in all_sessions if s["anomaly"] == 1)
    print(f"  Anomalous sessions: {anomalous} ({100*anomalous/len(all_sessions):.1f}%)")

    return all_sessions


def _build_session_dict(
    user: str,
    session_index: int,
    events: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Packages a list of event dicts into a session dict.

    The session's anomaly label is 1 if ANY event in the session is anomalous.
    This matches the real UEBA use case: one malicious action in a session
    makes the whole session suspicious.
    """
    session_anomaly = 1 if any(e.get("Anomaly", 0) == 1 for e in events) else 0

    return {
        "session_id": f"SPEDIA_{user}_{session_index:04d}",
        "user_id":    user,
        "anomaly":    session_anomaly,
        "events":     events,
    }


def _row_to_event_dict(row: pd.Series) -> Dict[str, Any]:
    """
    Converts one CSV row (a pandas Series) into an event dict.

    We convert NaN values to empty string or 0 to avoid errors downstream.
    pandas reads missing CSV cells as float NaN — Python code checking
    'if event["Command"]' would crash on NaN, but works fine on "".
    """

    def safe_str(val) -> str:
        """Convert value to string; return empty string for NaN/None."""
        if pd.isna(val):
            return ""
        return str(val).strip()

    def safe_float(val) -> float:
        """Convert value to float; return 0.0 for NaN/None."""
        try:
            if pd.isna(val):
                return 0.0
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def safe_int(val) -> int:
        """Convert value to int; return 0 for NaN/None."""
        try:
            if pd.isna(val):
                return 0
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    # Build the timestamp string in ISO 8601 format
    ts = row["Timestamp"]
    timestamp_str = ts.isoformat() + "Z" if not pd.isna(ts) else ""

    return {
        "event_id":     safe_str(row.get("id")),
        "user_id":      safe_str(row.get("User")),
        "timestamp":    timestamp_str,
        "Activity":     safe_str(row.get("Activity")),
        "Action":       safe_str(row.get("Action")),
        "Level":        safe_float(row.get("Level")),
        "Command":      safe_str(row.get("Command")),
        "file_path":    safe_str(row.get("Path")),
        "Filename":     safe_str(row.get("Filename")),
        "bytes":        safe_float(row.get("Size")),
        "IsAfterHours": safe_int(row.get("IsAfterHours")),
        "IsWeekend":    safe_int(row.get("IsWeekend")),
        "Hour":         safe_int(row.get("Hour")),
        "DayOfWeek":    safe_int(row.get("DayOfWeek")),
        "CTMC_State":   safe_str(row.get("CTMC_State")),
        "Anomaly":      safe_int(row.get("Anomaly")),
        # Pass through all pre-computed rule flags
        # These let you validate your rule engine against SPEDIA's ground truth
        **{
            col: safe_int(row.get(col))
            for col in row.index
            if col.startswith("Rule_")
        }
    }


if __name__ == "__main__":
    # Quick sanity test — run this directly to verify the loader works
    # Command: python analytics/data/spedia/loader.py
    import sys
    import os

    csv_path = "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv"

    if not os.path.exists(csv_path):
        print(f"ERROR: File not found: {csv_path}")
        print("Make sure you run this from the repo root: cd /workspaces/UEBA")
        sys.exit(1)

    sessions = load_spedia_sessions(csv_path)

    print("\n--- Sample session ---")
    s = sessions[0]
    print(f"Session ID:  {s['session_id']}")
    print(f"User:        {s['user_id']}")
    print(f"Anomaly:     {s['anomaly']}")
    print(f"Event count: {len(s['events'])}")
    print(f"First event: {s['events'][0].get('CTMC_State')} | {s['events'][0].get('Action')}")

    print("\nDone. Loader is working correctly.")
