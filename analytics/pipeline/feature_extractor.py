from typing import Dict, Any
from datetime import datetime

class FeatureExtractor:
    """
    Extracts purely numerical V2 behavioral features from raw session dicts.
    GUARANTEE: absolutely zero target leakage (Risk_Score, Rules, Anomaly).
    """

    def __init__(self):
        # We define a stable ordered list of feature keys for matrix conversion.
        self.feature_names = [
            "session_duration",
            "event_count",
            "is_after_hours",
            "is_weekend",
            "login_count",
            "failed_login_count",
            "file_access",
            "file_modify",
            "file_add",
            "file_delete",
            "unique_files",
            "email_count",
            "command_count",
            "suspicious_command",
            "privilege_command",
            "recon_command",
        ]

    def extract_features(self, session: Dict[str, Any]) -> Dict[str, float]:
        """
        Takes a session dict (from loader.load_spedia_sessions)
        and outputs a dictionary of numerical features.
        """
        events = session.get("events", [])
        if not events:
            return {k: 0.0 for k in self.feature_names}

        session_duration = 0.0
        try:
            ts_list = [e["timestamp"] for e in events if e.get("timestamp")]
            if ts_list:
                import pandas as pd
                times = pd.to_datetime(ts_list, format='mixed', utc=True)
                session_duration = (times.max() - times.min()).total_seconds()
        except Exception:
            pass

        # Flags extraction
        is_after_hours = 1.0 if any(e.get("IsAfterHours") == 1 for e in events) else 0.0
        is_weekend     = 1.0 if any(e.get("IsWeekend") == 1 for e in events) else 0.0

        # Unique paths representation
        files = {e.get("file_path") for e in events if e.get("file_path")}
        unique_files = len(files)

        # Counting occurrences based on CTMC_State and specific native actions
        features = {
            "session_duration": session_duration,
            "event_count": float(len(events)),
            "is_after_hours": is_after_hours,
            "is_weekend": is_weekend,
            "login_count": sum(1.0 for e in events if e.get("CTMC_State") == "Login"),
            "failed_login_count": sum(1.0 for e in events if e.get("CTMC_State") == "Login_Failed"),
            "file_access": sum(1.0 for e in events if e.get("CTMC_State") == "File_Access"),
            "file_modify": sum(1.0 for e in events if e.get("CTMC_State") == "File_Modify"),
            "file_add": sum(1.0 for e in events if e.get("CTMC_State") == "File_Add"),
            "file_delete": sum(1.0 for e in events if e.get("CTMC_State") == "File_Delete"),
            "unique_files": float(unique_files),
            "email_count": sum(1.0 for e in events if e.get("CTMC_State") == "Email"),
            "command_count": sum(1.0 for e in events if e.get("CTMC_State") == "Command"),
            "suspicious_command": sum(1.0 for e in events if e.get("CTMC_State") == "Suspicious_Command"),
            "privilege_command": sum(1.0 for e in events if e.get("CTMC_State") == "Privilege_Command"),
            "recon_command": sum(1.0 for e in events if e.get("CTMC_State") == "Recon_Command"),
        }

        # Ensure all feature_names are present
        return {k: features.get(k, 0.0) for k in self.feature_names}
