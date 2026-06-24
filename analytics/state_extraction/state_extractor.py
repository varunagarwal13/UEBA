# analytics/state_extraction/state_extractor.py
#
# PURPOSE: Convert raw SPEDIA events into CTMC state strings
# INPUT:   A session dict from the SPEDIA loader
# OUTPUT:  Ordered list of state strings from the 14-state SPEDIA vocabulary
#
# The 14 SPEDIA states (confirmed from ctmc_session_sequences.csv):
#   Login, Login_Failed, Logout, Browser, Email,
#   File_Access, File_Modify, File_Add, File_Delete,
#   Command, Suspicious_Command, Privilege_Command, Recon_Command, Device_Event

from typing import List, Dict, Any, Optional

RECON_COMMANDS = {
    "whoami", "id", "w", "who", "last", "lastlog", "ps", "netstat",
    "ss", "ifconfig", "ip", "arp", "ls", "find", "locate", "env",
    "printenv", "uname", "hostname", "df", "du", "lsof", "lsblk",
    "cat /etc/passwd", "cat /etc/shadow"
}

PRIVILEGE_COMMANDS = {
    "sudo", "su", "passwd", "chown", "chmod", "visudo", "useradd",
    "usermod", "groupadd", "systemctl", "service", "iptables",
    "mount", "fdisk", "cryptsetup"
}

SUSPICIOUS_LEVEL_THRESHOLD = 8.0


class StateExtractor:

    def extract_states(self, session: Dict[str, Any]) -> List[str]:
        states = []
        for event in session.get("events", []):
            # If SPEDIA pre-computed the state, use it directly
            precomputed = event.get("CTMC_State", "").strip()
            if precomputed:
                states.append(precomputed)
            else:
                # Derive the state ourselves (for live/new events)
                state = self._classify_event(event)
                if state:
                    states.append(state)
        return states

    def _classify_event(self, event: Dict[str, Any]) -> Optional[str]:
        activity = str(event.get("Activity", "")).lower().strip()
        action   = str(event.get("Action",   "")).lower().strip()
        level    = float(event.get("Level",   0) or 0)
        command  = str(event.get("Command",   "")).lower().strip()

        if activity == "session":
            if "failed" in action or "error" in action or level >= SUSPICIOUS_LEVEL_THRESHOLD:
                return "Login_Failed"
            elif "logout" in action or "closed" in action:
                return "Logout"
            return "Login"

        if activity == "command":
            if any(r in command for r in RECON_COMMANDS):
                return "Recon_Command"
            if any(p in command for p in PRIVILEGE_COMMANDS):
                return "Privilege_Command"
            if level >= SUSPICIOUS_LEVEL_THRESHOLD:
                return "Suspicious_Command"
            return "Command"

        if activity == "file":
            if "delet" in action or "remov" in action:
                return "File_Delete"
            if "add" in action or "creat" in action:
                return "File_Add"
            if "modif" in action or "writ" in action:
                return "File_Modify"
            return "File_Access"

        if activity == "email":
            return "Email"

        if activity in ("browser", "http", "web", "url"):
            return "Browser"

        if activity in ("network", "device", "usb", "hardware"):
            return "Device_Event"

        return None
