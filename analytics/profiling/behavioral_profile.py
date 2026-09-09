from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class ProfileStatistics:
    count: int = 0
    mean: float = 0.0
    variance: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0

@dataclass
class BehavioralProfileState:
    """
    In-memory representation of a user's behavioral profile.
    Maps directly to `models.PersonalBehaviorProfile` JSON payloads.
    """
    user_id: str
    session_count: int = 0
    statistics: Dict[str, ProfileStatistics] = field(default_factory=dict)
    state_distribution: Dict[str, float] = field(default_factory=dict)
    action_distribution: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0

    def get_profile_state(self) -> str:
        """Determines statistical maturity."""
        if self.session_count < 5:
            return "NEW"
        elif self.session_count < 15:
            return "LEARNING"
        else:
            return "ESTABLISHED"
