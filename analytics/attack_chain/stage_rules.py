from analytics.attack_chain.attack_stage import AttackStage, get_stage_severity
from typing import Dict, Any, List, Optional, Tuple

# Executable name (first token, basename) -> stage.
# Kept to tools whose purpose is unambiguous; everyday utilities (ls, mkdir, echo,
# grep) are deliberately absent so ordinary admin sessions stay UNKNOWN.
COMMAND_STAGES = {
    # host / network reconnaissance
    "nmap": AttackStage.RECONNAISSANCE, "masscan": AttackStage.RECONNAISSANCE,
    "whoami": AttackStage.RECONNAISSANCE, "id": AttackStage.RECONNAISSANCE,
    "ifconfig": AttackStage.RECONNAISSANCE, "ip": AttackStage.RECONNAISSANCE,
    "netstat": AttackStage.RECONNAISSANCE, "ss": AttackStage.RECONNAISSANCE,
    "uname": AttackStage.RECONNAISSANCE, "hostname": AttackStage.RECONNAISSANCE,
    "ipconfig": AttackStage.RECONNAISSANCE, "arp": AttackStage.RECONNAISSANCE,
    # searching for interesting data
    "find": AttackStage.DISCOVERY, "locate": AttackStage.DISCOVERY,
    # credential cracking, exploitation, permission changes
    "john": AttackStage.PRIVILEGE_ESCALATION, "hashcat": AttackStage.PRIVILEGE_ESCALATION,
    "msfconsole": AttackStage.PRIVILEGE_ESCALATION, "sudo": AttackStage.PRIVILEGE_ESCALATION,
    "su": AttackStage.PRIVILEGE_ESCALATION, "chmod": AttackStage.PRIVILEGE_ESCALATION,
    "chown": AttackStage.PRIVILEGE_ESCALATION,
    # reading file contents
    "cat": AttackStage.COLLECTION, "head": AttackStage.COLLECTION,
    "tail": AttackStage.COLLECTION, "less": AttackStage.COLLECTION,
    # packaging / encoding before transfer
    "base64": AttackStage.STAGING, "tar": AttackStage.STAGING, "zip": AttackStage.STAGING,
    "gzip": AttackStage.STAGING, "7z": AttackStage.STAGING, "rar": AttackStage.STAGING,
    # services and scheduled tasks that survive reboot
    "systemctl": AttackStage.PERSISTENCE, "service": AttackStage.PERSISTENCE,
    "crontab": AttackStage.PERSISTENCE, "schtasks": AttackStage.PERSISTENCE,
    # moving data off the host
    "nc": AttackStage.EXFILTRATION, "ncat": AttackStage.EXFILTRATION,
    "netcat": AttackStage.EXFILTRATION, "ftp": AttackStage.EXFILTRATION,
    "scp": AttackStage.EXFILTRATION, "sftp": AttackStage.EXFILTRATION,
    "rsync": AttackStage.EXFILTRATION,
}

# Writes under these paths change what runs at boot / login.
PERSISTENCE_PATHS = (
    "/etc/systemd", "/etc/cron", "/var/spool/cron", "/etc/init.d", "/etc/rc.local",
    "/usr/bin", "/usr/sbin", "/usr/local/bin", "/etc/ld.so", "/.ssh/authorized_keys",
    "/.bashrc", "/.profile",
)

RULE_STAGES = {
    "multiple failed logins": AttackStage.AUTHENTICATION,
    "failed logins then successful login": AttackStage.AUTHENTICATION,
    "privilege escalation": AttackStage.PRIVILEGE_ESCALATION,
    "bulk file access": AttackStage.COLLECTION,
    "privilege escalation then data access": AttackStage.COLLECTION,
    "file access then email": AttackStage.EXFILTRATION,
    "file access then upload": AttackStage.EXFILTRATION,
    "mass file exfil": AttackStage.EXFILTRATION,
}

FAILED_LOGIN_ACTIONS = ("login failed", "multiple failed logins", "auth:failure")


def _tool(command: str) -> str:
    first = command.strip().split(" ", 1)[0] if command else ""
    return first.rsplit("/", 1)[-1].lower()


def _event_stage(event: Dict[str, Any]) -> Optional[Tuple[AttackStage, str]]:
    """Stage implied by a single event, with a short human-readable reason."""
    activity = str(event.get("Activity", "")).lower()
    action = str(event.get("Action", "")).lower()

    tool = _tool(str(event.get("Command", "")))
    if tool in COMMAND_STAGES:
        return COMMAND_STAGES[tool], f"{tool} executed"

    if activity == "session" and any(a in action for a in FAILED_LOGIN_ACTIONS):
        return AttackStage.AUTHENTICATION, "failed login"

    if activity == "file" and ("added" in action or "modified" in action):
        path = str(event.get("file_path", ""))
        if any(p in path for p in PERSISTENCE_PATHS):
            return AttackStage.PERSISTENCE, f"write to {path[:60]}"

    return None


class StageMapper:
    """Maps rule violations and per-event evidence to kill-chain stages."""

    @staticmethod
    def map_session_stages(session: Dict[str, Any], active_rules: List[str]) -> List[Dict[str, Any]]:
        """
        Every stage evidenced in the session, in the order it first appears, as
        {"stage", "evidence", "timestamp"}. Rule-derived stages are placed by
        kill-chain severity since rules have no single event time.
        """
        found: Dict[AttackStage, Dict[str, Any]] = {}

        for ev in session.get("events", []):
            hit = _event_stage(ev)
            if hit and hit[0] not in found:
                found[hit[0]] = {"stage": hit[0].value, "evidence": hit[1], "timestamp": ev.get("timestamp") or None}

        # Removable-media use is deliberately not a stage signal: on SPEDIA, sessions with a
        # device connect plus file activity are only ~15% anomalous, so it mostly adds noise.

        for rule in active_rules or []:
            stage = RULE_STAGES.get(str(rule).lower())
            if stage and stage not in found:
                found[stage] = {"stage": stage.value, "evidence": f"rule: {rule}", "timestamp": None}

        # Legacy single-event payloads that carry action/event_type at the top level
        if not found:
            legacy = StageMapper._legacy_stage(session)
            if legacy != AttackStage.UNKNOWN:
                found[legacy] = {"stage": legacy.value, "evidence": "session action", "timestamp": None}

        timed = [v for v in found.values() if v["timestamp"]]
        untimed = [v for v in found.values() if not v["timestamp"]]
        timed.sort(key=lambda v: v["timestamp"])
        untimed.sort(key=lambda v: get_stage_severity(AttackStage(v["stage"])))
        return timed + untimed

    @staticmethod
    def map_session(session: Dict[str, Any], active_rules: List[str]) -> AttackStage:
        """Most advanced stage evidenced in the session (UNKNOWN if none)."""
        stages = [AttackStage(s["stage"]) for s in StageMapper.map_session_stages(session, active_rules)]
        return max(stages, key=get_stage_severity) if stages else AttackStage.UNKNOWN

    @staticmethod
    def _legacy_stage(session: Dict[str, Any]) -> AttackStage:
        action = str(session.get("action", "")).lower()
        event_type = str(session.get("event_type", "")).lower()
        tool = _tool(action)
        if event_type == "login" or "auth:failure" in action:
            return AttackStage.AUTHENTICATION
        if tool in COMMAND_STAGES:
            return COMMAND_STAGES[tool]
        if event_type == "file_access" and "read" in action:
            return AttackStage.COLLECTION
        if event_type == "email" and "attachment" in action:
            return AttackStage.EXFILTRATION
        return AttackStage.UNKNOWN
