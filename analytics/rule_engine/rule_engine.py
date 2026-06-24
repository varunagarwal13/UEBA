# analytics/rule_engine/rule_engine.py
#
# PURPOSE: Check session state sequences against security rules.
#
# v2 changes:
#   Added R07 (excessive commands) and R16 (bulk file access)
#   to catch volume-based anomalies that CTMC misses.
#   These two rules target the 54 anomalous sessions that scored
#   below 10 in our threshold analysis — sessions that look normal
#   in terms of state transitions but are unusual in volume.

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class RuleViolation:
    rule_id:            str
    rule_name:          str
    severity:           str
    score_contribution: float
    description:        str


class RuleEngine:

    def check_all_rules(
        self,
        state_sequence: List[str],
        events: List[Dict[str, Any]]
    ) -> List[RuleViolation]:
        violations = []
        for check in [
            self._r01_after_hours_login,
            self._r03_login_failed,
            self._r04_multiple_failed_logins,
            self._r07_excessive_commands,
            self._r16_bulk_file_access,
            self._r25_privilege_escalation,
            self._r27_after_hours_then_file,
            self._r28_failed_then_success,
            self._r29_sensitive_then_email,
            self._r30_sensitive_then_upload,
            self._r32_priv_then_data,
        ]:
            v = check(state_sequence, events)
            if v:
                violations.append(v)
        return violations

    # ------------------------------------------------------------------
    # SINGLE-EVENT RULES
    # ------------------------------------------------------------------

    def _r01_after_hours_login(self, states, events):
        for e in events:
            if e.get("CTMC_State") == "Login" and e.get("IsAfterHours") == 1:
                return RuleViolation(
                    "R01", "After-hours login", "Medium", 15.0,
                    "User logged in outside normal working hours.")
        return None

    def _r03_login_failed(self, states, events):
        if "Login_Failed" in states:
            return RuleViolation(
                "R03", "Login failed", "Low", 8.0,
                "One or more failed login attempts in this session.")
        return None

    def _r04_multiple_failed_logins(self, states, events):
        n = states.count("Login_Failed")
        if n >= 3:
            return RuleViolation(
                "R04", "Multiple failed logins", "High", 25.0,
                f"{n} failed login attempts — possible brute force.")
        return None

    def _r07_excessive_commands(self, states, events):
        """
        NEW RULE — catches volume-based command anomalies.

        What it detects: sessions with an unusually high number of
        Command + Suspicious_Command + Recon_Command states.

        Why this matters: attackers running scripts, enumeration tools,
        or automated exfiltration generate far more commands than a
        normal user session. This rule catches sessions that look
        "normal" individually but are suspicious in volume.

        Threshold: 20 command-type states in one session.
        This was chosen by inspecting the SPEDIA data — normal users
        rarely exceed 15 command events in one session.
        """
        command_states = {"Command", "Suspicious_Command",
                          "Recon_Command", "Privilege_Command"}
        n = sum(1 for s in states if s in command_states)
        if n >= 20:
            return RuleViolation(
                "R07", "Excessive command execution", "High", 20.0,
                f"{n} command-type events in one session — "
                "may indicate scripted or automated activity.")
        return None

    def _r16_bulk_file_access(self, states, events):
        """
        NEW RULE — catches bulk file access anomalies.

        What it detects: sessions with an unusually high number of
        File_Access + File_Modify + File_Add + File_Delete states.

        Why this matters: data staging before exfiltration involves
        touching many files in a short time. A user accessing 30+
        files in one session is statistically unusual and warrants
        investigation.

        Threshold: 15 file-type states in one session.
        """
        file_states = {"File_Access", "File_Modify", "File_Add", "File_Delete"}
        n = sum(1 for s in states if s in file_states)
        if n >= 15:
            return RuleViolation(
                "R16", "Bulk file access", "Medium", 18.0,
                f"{n} file operations in one session — "
                "unusual volume may indicate data staging.")
        return None

    def _r25_privilege_escalation(self, states, events):
        if "Privilege_Command" in states:
            return RuleViolation(
                "R25", "Privilege escalation", "High", 30.0,
                "A privilege-escalating command was executed.")
        return None

    # ------------------------------------------------------------------
    # SEQUENCE RULES
    # ------------------------------------------------------------------

    def _r27_after_hours_then_file(self, states, events):
        after_hours = [
            e for e in events
            if e.get("CTMC_State") == "Login" and e.get("IsAfterHours") == 1
        ]
        has_file = any(s in states for s in ("File_Access", "File_Modify"))
        if after_hours and has_file:
            return RuleViolation(
                "R27", "After-hours login then file access", "High", 30.0,
                "After-hours login followed by file access.")
        return None

    def _r28_failed_then_success(self, states, events):
        if "Login_Failed" in states and "Login" in states:
            fi = states.index("Login_Failed")
            si = next(
                (i for i, s in enumerate(states) if s == "Login" and i > fi),
                -1
            )
            if si > fi:
                return RuleViolation(
                    "R28", "Failed logins then successful login", "High", 25.0,
                    "Failed login attempts followed by a successful login.")
        return None

    def _r29_sensitive_then_email(self, states, events):
        file_states = {"File_Access", "File_Modify"}
        has_file  = any(s in file_states for s in states)
        has_email = "Email" in states
        if has_file and has_email:
            fi = next(i for i, s in enumerate(states) if s in file_states)
            ei = next(
                (i for i, s in enumerate(states) if s == "Email" and i > fi),
                -1
            )
            if ei > fi:
                return RuleViolation(
                    "R29", "File access then email", "High", 30.0,
                    "File accessed then email sent in same session.")
        return None

    def _r30_sensitive_then_upload(self, states, events):
        file_states   = {"File_Access", "File_Modify"}
        upload_states = {"File_Add"}
        has_file   = any(s in file_states   for s in states)
        has_upload = any(s in upload_states for s in states)
        if has_file and has_upload:
            return RuleViolation(
                "R30", "File access then upload", "Critical", 40.0,
                "File access followed by file-add (potential exfiltration).")
        return None

    def _r32_priv_then_data(self, states, events):
        if "Privilege_Command" in states:
            pi = states.index("Privilege_Command")
            data_states = {"File_Access", "File_Modify", "File_Add", "Email"}
            di = next(
                (i for i, s in enumerate(states)
                 if s in data_states and i > pi),
                -1
            )
            if di > pi:
                return RuleViolation(
                    "R32", "Privilege escalation then data access",
                    "Critical", 45.0,
                    "Privilege escalation followed by data access.")
        return None
