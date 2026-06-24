# analytics/rule_engine/rule_engine.py
#
# SURGICAL FIXES based on false positive / false negative analysis:
#
# FALSE POSITIVES fixed:
#   R16 threshold raised: 8 → 20 (camilo/humberto are legitimate heavy users
#       with 250+ state sessions. Firing at 8 file ops was too sensitive.)
#   R29 now requires BOTH file access AND email in session with length > 15
#       (irene's 6 FPs were tiny 12-27 state sessions where one file access
#       and one email happened to coexist — not a meaningful pattern)
#
# FALSE NEGATIVES fixed:
#   R37 NEW — repeated login-only sessions
#       root(uid=0): 21 missed, ubuntu(uid=1000): 10 missed,
#       wazuh(uid=129): 6 missed — all sessions containing ONLY Login states.
#       SPEDIA labels these as malicious because they represent
#       automated credential stuffing or account enumeration.
#       A session of 8+ Login events with nothing else is suspicious.

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
        events:         List[Dict[str, Any]],
        user_id:        str = ""
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
            self._r29_file_then_email,
            self._r30_file_then_upload,
            self._r32_priv_then_data,
            self._r35_high_wazuh_level,
            self._r37_login_only_session,
        ]:
            v = check(state_sequence, events)
            if v:
                violations.append(v)
        return violations

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
        cmd_states = {"Command", "Suspicious_Command",
                      "Recon_Command", "Privilege_Command"}
        n = sum(1 for s in states if s in cmd_states)
        if n >= 10:
            return RuleViolation(
                "R07", "Excessive command execution", "High", 20.0,
                f"{n} command-type events in one session.")
        return None

    def _r16_bulk_file_access(self, states, events):
        # Raised from 8 to 20 — camilo and humberto are legitimate heavy
        # users with 250+ state sessions. 8 file ops in 250 states is
        # completely normal. 20 is still suspicious for regular users.
        file_states = {"File_Access", "File_Modify", "File_Add", "File_Delete"}
        n = sum(1 for s in states if s in file_states)
        if n >= 20:
            return RuleViolation(
                "R16", "Bulk file access", "Medium", 18.0,
                f"{n} file operations in one session.")
        return None

    def _r25_privilege_escalation(self, states, events):
        if "Privilege_Command" in states:
            return RuleViolation(
                "R25", "Privilege escalation", "High", 30.0,
                "A privilege-escalating command was executed.")
        return None

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
                    "Failed login attempts followed by successful login.")
        return None

    def _r29_file_then_email(self, states, events):
        # Added minimum session length check (15 states).
        # Irene's false positives were tiny sessions (12-27 states) where
        # one file access and one email coexisted by chance.
        # In a session of 15+ states this pattern is meaningful.
        if len(states) < 15:
            return None
        file_states = {"File_Access", "File_Modify"}
        has_file  = any(s in file_states for s in states)
        has_email = "Email" in states
        if has_file and has_email:
            fi = next(i for i, s in enumerate(states) if s in file_states)
            ei = next(
                (i for i, s in enumerate(states)
                 if s == "Email" and i > fi), -1
            )
            if ei > fi:
                return RuleViolation(
                    "R29", "File access then email", "High", 30.0,
                    "File accessed then email sent in same session.")
        return None

    def _r30_file_then_upload(self, states, events):
        file_states   = {"File_Access", "File_Modify"}
        upload_states = {"File_Add"}
        if (any(s in file_states   for s in states) and
                any(s in upload_states for s in states)):
            return RuleViolation(
                "R30", "File access then upload", "Critical", 40.0,
                "File access followed by file creation.")
        return None

    def _r32_priv_then_data(self, states, events):
        if "Privilege_Command" in states:
            pi = states.index("Privilege_Command")
            data_states = {"File_Access", "File_Modify", "File_Add", "Email"}
            di = next(
                (i for i, s in enumerate(states)
                 if s in data_states and i > pi), -1
            )
            if di > pi:
                return RuleViolation(
                    "R32", "Privilege escalation then data access",
                    "Critical", 45.0,
                    "Privilege escalation followed by data access.")
        return None

    def _r35_high_wazuh_level(self, states, events):
        max_level = max(
            (float(e.get("Level", 0) or 0) for e in events),
            default=0.0
        )
        if max_level >= 10.0:
            return RuleViolation(
                "R35", "High Wazuh alert level", "High", 25.0,
                f"Wazuh alert level {max_level:.0f}/15.")
        return None

    def _r37_login_only_session(self, states, events):
        """
        NEW RULE targeting the biggest source of missed threats.

        root(uid=0) had 21 missed threats, ubuntu(uid=1000) had 10,
        wazuh(uid=129) had 6. ALL of them were sessions containing
        only Login states — nothing else.

        In SPEDIA, these represent automated credential attacks:
        an attacker (or malware) is repeatedly authenticating as a
        service account, which generates many Login events with no
        subsequent activity (because the goal is persistence,
        not data access).

        A session of 5+ Login events with NO other state type
        is not normal system behavior — it is authentication anomaly.

        Why 5? Normal PAM authentication generates 1-2 Login events
        per actual login. 5+ with nothing else = automated behavior.
        """
        if len(states) < 5:
            return None

        non_login = [s for s in states if s not in ("Login", "Logout")]
        login_count = states.count("Login")

        # Session is dominated by Login states with nothing else
        if login_count >= 5 and len(non_login) == 0:
            return RuleViolation(
                "R37", "Repeated login-only session", "High", 30.0,
                f"{login_count} login events with no subsequent activity — "
                "possible automated credential attack.")
        return None
