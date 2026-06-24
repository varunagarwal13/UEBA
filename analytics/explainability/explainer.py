# analytics/explainability/explainer.py
#
# PURPOSE: Convert detection results into human-readable explanations
#          that a SOC analyst can read and act on in 30 seconds.
#
# WHY THIS MODULE EXISTS:
#   Without explainability, an analyst sees:
#     "User irene — Risk Score: 92 — Severity: Critical"
#   With explainability, they see:
#     "irene logged in at 2:14 AM, accessed 47 files, escalated privileges,
#      then sent an email to an external address. This sequence has never
#      been observed in this user's history."
#
#   The difference is the analyst can make a decision in 30 seconds
#   instead of spending 20 minutes manually reviewing raw logs.
#
# INPUT:  alert_id, user_id, state_sequence, rule_violations, risk_result
# OUTPUT: ExplanationResult with summary, reasons, timeline, actions
#
# POSITION IN PIPELINE:
#   RiskScorer → Explainer → Backend → Frontend dashboard

from typing import List, Dict, Any
from dataclasses import dataclass, field


# Maps technical CTMC state names to plain English
# that a non-technical SOC analyst can understand
STATE_TO_HUMAN = {
    "Login":              "User logged in successfully",
    "Login_Failed":       "Login attempt failed",
    "Logout":             "User logged out",
    "Browser":            "Web browsing activity",
    "Email":              "Email activity",
    "File_Access":        "File was accessed (read)",
    "File_Modify":        "File was modified",
    "File_Add":           "New file was created or uploaded",
    "File_Delete":        "File was deleted",
    "Command":            "System command executed",
    "Suspicious_Command": "Suspicious system command executed",
    "Privilege_Command":  "Privileged command executed (sudo/su)",
    "Recon_Command":      "Reconnaissance command executed (whoami/netstat/ps)",
    "Device_Event":       "Hardware or device event detected",
}

# Maps rule IDs to analyst-facing explanations.
# These are more detailed than the rule engine descriptions —
# they include context about why the pattern is suspicious.
RULE_TO_EXPLANATION = {
    "R01": (
        "Login occurred outside normal working hours (before 8 AM or after 8 PM). "
        "After-hours access is a common pattern in insider threat incidents, "
        "particularly when combined with sensitive file access."
    ),
    "R03": (
        "One or more login attempts failed in this session. "
        "This may indicate incorrect credentials, a locked account, "
        "or an unauthorized access attempt."
    ),
    "R04": (
        "Three or more consecutive login failures were detected. "
        "This pattern is consistent with brute-force attacks or "
        "credential stuffing by an automated tool."
    ),
    "R07": (
        "An unusually high number of system commands were executed in this session. "
        "This may indicate automated scripting, data collection tools, "
        "or an attacker running enumeration commands."
    ),
    "R16": (
        "An unusually high number of file operations occurred in this session. "
        "Bulk file access is a common precursor to data exfiltration — "
        "the user may be staging data for transfer."
    ),
    "R25": (
        "A privilege escalation command (sudo, su, or similar) was executed. "
        "Privilege escalation is used to gain access to resources beyond "
        "the user's normal authorization level."
    ),
    "R27": (
        "The user logged in outside working hours and subsequently accessed files. "
        "This combination — after-hours login followed by file activity — "
        "is one of the strongest indicators of insider data theft."
    ),
    "R28": (
        "Multiple failed login attempts were followed by a successful login. "
        "This sequence suggests the user (or an attacker using their credentials) "
        "needed multiple attempts before gaining access."
    ),
    "R29": (
        "File access was followed by email activity in the same session. "
        "This pattern may indicate the user accessed files and then "
        "sent their contents (or references to them) via email."
    ),
    "R30": (
        "File access was followed by file creation or upload in the same session. "
        "This is consistent with the 'stage and exfiltrate' pattern — "
        "accessing data then copying it to a new location."
    ),
    "R32": (
        "Privilege escalation was immediately followed by data access. "
        "This is a high-confidence indicator of malicious intent — "
        "the user escalated privileges specifically to access restricted data."
    ),
    "R35": (
        "Wazuh (the security monitoring system) assigned a high severity level "
        "to one or more events in this session. This means the underlying "
        "security platform itself flagged this activity as suspicious."
    ),
    "R37": (
        "This session contained only repeated login events with no other activity. "
        "This pattern is consistent with automated credential attacks "
        "or account enumeration by malware."
    ),
}

# Recommended analyst actions based on severity and rule combinations
ACTIONS_BY_SEVERITY = {
    "Critical": [
        "Immediately review the full session event log in the investigation panel",
        "Consider temporarily suspending the user account pending investigation",
        "Notify the security manager and initiate incident response procedure",
        "Preserve all logs related to this session for forensic analysis",
    ],
    "High": [
        "Review the full session event log within 1 hour",
        "Verify with the user's manager whether this activity was authorized",
        "Check if any data left the organization (review email and upload logs)",
    ],
    "Medium": [
        "Schedule a review of this session within 24 hours",
        "Check if this activity pattern has occurred before for this user",
    ],
    "Low": [
        "Log for trend analysis",
        "No immediate action required unless pattern repeats",
    ],
}

# Additional targeted actions for specific rules
RULE_SPECIFIC_ACTIONS = {
    "R30": "Verify whether the uploaded file contained sensitive or confidential data",
    "R29": "Review the email recipient — check if it is an external or personal address",
    "R25": "Check what commands were run under elevated privileges",
    "R32": "Identify which restricted resources were accessed after privilege escalation",
    "R04": "Check the source IP address of the failed login attempts",
    "R37": "Investigate whether the account credentials may have been compromised",
    "R35": "Review the specific Wazuh alerts that triggered the high severity level",
}


@dataclass
class ExplanationResult:
    """
    Complete human-readable explanation for one alert.
    Every field maps directly to a UI element in the SOC dashboard.
    """
    alert_id:   str
    user_id:    str

    # One-paragraph narrative summary — shown at the top of the alert card
    summary: str = ""

    # Bullet-point list of reasons — shown as the "Why was this flagged?" section
    reasons: List[str] = field(default_factory=list)

    # Human-readable timeline — shown in the "Session timeline" panel
    timeline: List[str] = field(default_factory=list)

    # Condensed timeline for compact display (deduplicated consecutive states)
    timeline_compact: List[str] = field(default_factory=list)

    # What the analyst should do — shown as "Recommended actions"
    recommended_actions: List[str] = field(default_factory=list)

    # Risk level context — shown as a tooltip or sidebar note
    risk_context: str = ""

    # Which detection methods fired — shown in "Detection breakdown"
    detection_methods: List[str] = field(default_factory=list)


class Explainer:
    """
    Generates human-readable explanations from detection results.

    Design principle: every piece of text this class produces
    should be readable by a non-technical SOC analyst with no
    knowledge of CTMC, Markov chains, or anomaly detection.
    """

    def explain(
        self,
        alert_id:       str,
        user_id:        str,
        state_sequence: List[str],
        violations:     List[Any],   # List[RuleViolation]
        risk_score:     float,
        severity:       str,
        ctmc_score:     float,
        rule_score:     float,
        confidence:     float,
    ) -> ExplanationResult:
        """
        Generates the complete explanation for one alert.

        Parameters:
            alert_id:       unique alert identifier
            user_id:        the user being investigated
            state_sequence: ordered list of CTMC states from StateExtractor
            violations:     list of RuleViolation objects from RuleEngine
            risk_score:     final 0-100 composite score
            severity:       Low / Medium / High / Critical
            ctmc_score:     CTMC component score (0-100)
            rule_score:     Rules component score (0-100)
            confidence:     confidence in the score (0.0-1.0)

        Returns: ExplanationResult with all fields populated
        """
        result = ExplanationResult(alert_id=alert_id, user_id=user_id)

        # Build each component
        result.timeline         = self._build_timeline(state_sequence)
        result.timeline_compact = self._build_compact_timeline(state_sequence)
        result.reasons          = self._build_reasons(violations, ctmc_score,
                                                       state_sequence)
        result.summary          = self._build_summary(user_id, severity,
                                                       violations, state_sequence,
                                                       risk_score)
        result.recommended_actions = self._build_actions(severity, violations)
        result.risk_context        = self._build_risk_context(
                                         risk_score, severity, confidence,
                                         ctmc_score, rule_score)
        result.detection_methods   = self._build_detection_methods(
                                         ctmc_score, rule_score, violations)

        return result

    # ------------------------------------------------------------------
    # PRIVATE BUILDER METHODS
    # ------------------------------------------------------------------

    def _build_timeline(self, state_sequence: List[str]) -> List[str]:
        """
        Converts every state in the sequence to a human-readable string.
        Preserves full order — one entry per event.
        Used in the detailed investigation view.
        """
        return [
            STATE_TO_HUMAN.get(state, state)
            for state in state_sequence
        ]

    def _build_compact_timeline(self, state_sequence: List[str]) -> List[str]:
        """
        Builds a deduplicated timeline for compact display.

        Consecutive identical states are collapsed with a count.
        Example:
          [Login, Browser, Browser, Browser, Email, File_Access, File_Access]
          becomes:
          ["User logged in", "Web browsing (x3)", "Email activity",
           "File was accessed (x2)"]

        Why: A session may have 500 events but only 8 distinct phases.
        The compact timeline shows the analyst the shape of the session
        without overwhelming them with repetition.
        """
        if not state_sequence:
            return []

        compact = []
        current = state_sequence[0]
        count   = 1

        for state in state_sequence[1:]:
            if state == current:
                count += 1
            else:
                label = STATE_TO_HUMAN.get(current, current)
                compact.append(f"{label} (x{count})" if count > 1 else label)
                current = state
                count   = 1

        # Don't forget the last group
        label = STATE_TO_HUMAN.get(current, current)
        compact.append(f"{label} (x{count})" if count > 1 else label)

        return compact

    def _build_reasons(
        self,
        violations:     List[Any],
        ctmc_score:     float,
        state_sequence: List[str],
    ) -> List[str]:
        """
        Builds the bullet-point list of reasons shown in the alert.

        Combines:
        1. One reason per rule violation (from RULE_TO_EXPLANATION)
        2. A CTMC reason if the sequence score is high
        3. State-specific observations for dangerous states present
        """
        reasons = []

        # Rule violation reasons — most specific and most actionable
        for v in violations:
            explanation = RULE_TO_EXPLANATION.get(v.rule_id)
            if explanation:
                reasons.append(explanation)
            else:
                # Fallback to the rule engine's description
                reasons.append(v.description)

        # CTMC reason — add if CTMC score is independently high
        # Only add this if there are few or no rule violations,
        # to avoid cluttering the explanation when rules already explain it
        if ctmc_score >= 60 and len(violations) < 3:
            reasons.append(
                f"The behavioral model detected an unusual activity sequence "
                f"(anomaly score: {ctmc_score:.0f}/100). This sequence deviates "
                f"significantly from this user's historical behavior patterns."
            )

        # State-specific observations for dangerous states with no rule
        # covering them — fills gaps when rules don't fire but states are present
        rule_ids = {v.rule_id for v in violations}
        dangerous_state_observations = {
            "Suspicious_Command": (
                "R33" not in rule_ids,
                "One or more commands were flagged as suspicious by the "
                "security monitoring system."
            ),
            "Recon_Command": (
                "R34" not in rule_ids,
                "Reconnaissance commands were executed — the user may have "
                "been gathering information about the system."
            ),
            "File_Delete": (
                True,
                "Files were deleted during this session. File deletion "
                "can indicate an attempt to cover tracks or sabotage."
            ),
        }

        for state, (should_add, observation) in dangerous_state_observations.items():
            if should_add and state in state_sequence:
                reasons.append(observation)

        # Deduplicate while preserving order
        seen = set()
        unique_reasons = []
        for r in reasons:
            if r not in seen:
                seen.add(r)
                unique_reasons.append(r)

        return unique_reasons

    def _build_summary(
        self,
        user_id:        str,
        severity:       str,
        violations:     List[Any],
        state_sequence: List[str],
        risk_score:     float,
    ) -> str:
        """
        Builds the one-paragraph narrative summary shown at the top
        of the alert card. This is what the analyst reads first.

        Strategy: mention who, what happened (top 2 rules), and how severe.
        Keep it to 2-3 sentences maximum.
        """
        severity_lower = severity.lower()
        n_events       = len(state_sequence)
        n_violations   = len(violations)

        if not violations:
            # Pure CTMC detection — no rules fired
            return (
                f"User {user_id} triggered a {severity_lower} risk alert "
                f"based on behavioral analysis. "
                f"The activity sequence in this {n_events}-event session "
                f"deviates significantly from this user's historical patterns. "
                f"No specific policy violations were detected, but the overall "
                f"behavior profile is unusual."
            )

        # Lead with the highest-severity violation
        sorted_violations = sorted(
            violations,
            key=lambda v: {"Critical": 4, "High": 3,
                           "Medium": 2, "Low": 1}.get(v.severity, 0),
            reverse=True
        )
        top_violation = sorted_violations[0]

        # Build compact description of what happened
        has_after_hours = any(v.rule_id == "R01" for v in violations)
        has_priv        = any(v.rule_id in ("R25", "R32") for v in violations)
        has_exfil       = any(v.rule_id in ("R29", "R30") for v in violations)
        has_brute       = any(v.rule_id in ("R03", "R04", "R28") for v in violations)

        what_happened = []
        if has_after_hours:
            what_happened.append("logged in outside working hours")
        if has_priv:
            what_happened.append("escalated system privileges")
        if has_exfil:
            what_happened.append("accessed and transferred files")
        if has_brute:
            what_happened.append("had multiple authentication failures")

        if what_happened:
            activity_desc = ", then ".join(what_happened)
            first_sentence = (
                f"User {user_id} {activity_desc} "
                f"in a {n_events}-event session."
            )
        else:
            first_sentence = (
                f"User {user_id} triggered {n_violations} security "
                f"policy violation(s) in a {n_events}-event session."
            )

        second_sentence = (
            f"The primary concern is: {top_violation.rule_name.lower()}. "
            if top_violation else ""
        )

        third_sentence = (
            f"Overall risk score: {risk_score:.0f}/100 ({severity}). "
            f"Analyst review is recommended."
        )

        return f"{first_sentence} {second_sentence}{third_sentence}"

    def _build_actions(
        self,
        severity:   str,
        violations: List[Any],
    ) -> List[str]:
        """
        Builds the recommended actions list.
        Combines severity-based actions with rule-specific actions.
        """
        actions = list(ACTIONS_BY_SEVERITY.get(severity, []))

        # Add rule-specific actions for the most severe violations
        rule_ids = {v.rule_id for v in violations}
        for rule_id, action in RULE_SPECIFIC_ACTIONS.items():
            if rule_id in rule_ids:
                actions.append(action)

        return actions

    def _build_risk_context(
        self,
        risk_score: float,
        severity:   str,
        confidence: float,
        ctmc_score: float,
        rule_score: float,
    ) -> str:
        """
        Builds the risk context tooltip text.
        Explains what the numbers mean in plain language.
        """
        confidence_pct = int(confidence * 100)
        confidence_label = (
            "high" if confidence >= 0.8 else
            "moderate" if confidence >= 0.5 else
            "low"
        )

        ctmc_contribution  = round(ctmc_score * 0.60, 1)
        rules_contribution = round(rule_score * 0.40, 1)

        return (
            f"Risk score {risk_score:.0f}/100 ({severity}). "
            f"Behavioral model contributed {ctmc_contribution:.0f} points, "
            f"policy rules contributed {rules_contribution:.0f} points. "
            f"Detection confidence is {confidence_label} ({confidence_pct}%). "
            f"{'This score is based on a well-established user profile.' if confidence >= 0.8 else 'Confidence is reduced because this user has limited behavioral history.'}"
        )

    def _build_detection_methods(
        self,
        ctmc_score: float,
        rule_score: float,
        violations: List[Any],
    ) -> List[str]:
        """
        Lists which detection methods contributed to this alert.
        Shown in the 'Detection breakdown' section of the dashboard.
        """
        methods = []

        if ctmc_score >= 10:
            methods.append(
                f"Behavioral model (CTMC): score {ctmc_score:.0f}/100 — "
                f"sequence anomaly detection"
            )

        if violations:
            rule_ids = ", ".join(v.rule_id for v in violations)
            methods.append(
                f"Rule engine: {len(violations)} violation(s) — "
                f"rules {rule_ids}"
            )

        if not methods:
            methods.append("No strong detection signal — review manually")

        return methods


    def build_timeline_brief(self, state_sequence, max_steps=8):
        """
        Builds an ultra-compact timeline for the alert card preview.
        Shows only the most security-relevant states, max 8 steps.
        Used by Person 3 for the alert list view (not the detail view).
        """
        # Priority states always shown if present
        priority = {
            "Login_Failed", "After_Hours_Login", "Privilege_Command",
            "Recon_Command", "Suspicious_Command", "File_Delete",
            "File_Add", "Email"
        }
        compact = self._build_compact_timeline(state_sequence)
        # First keep priority states
        brief = [s for s in compact
                 if any(p.replace("_"," ").lower() in s.lower()
                        for p in priority)]
        # Fill remaining slots with first states
        for s in compact:
            if s not in brief:
                brief.append(s)
            if len(brief) >= max_steps:
                break
        return brief[:max_steps]
