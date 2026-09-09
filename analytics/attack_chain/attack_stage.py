from enum import Enum

class AttackStage(Enum):
    AUTHENTICATION = "AUTHENTICATION" # Password sprays, weird off-hours logins
    RECONNAISSANCE = "RECONNAISSANCE" # internal network mapping
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION" # sudo / id changes
    DISCOVERY = "DISCOVERY" # looking for files
    COLLECTION = "COLLECTION" # hoarding mass files
    STAGING = "STAGING" # zipping files
    EXFILTRATION = "EXFILTRATION" # heavy outbound network transfers
    PERSISTENCE = "PERSISTENCE" # backdoor creation
    UNKNOWN = "UNKNOWN"

def get_stage_severity(stage: AttackStage) -> int:
    """Returns increasing severity bounds 1-10 mapped to kill-chain progression"""
    mapping = {
        AttackStage.AUTHENTICATION: 2,
        AttackStage.RECONNAISSANCE: 3,
        AttackStage.DISCOVERY: 4,
        AttackStage.PRIVILEGE_ESCALATION: 6,
        AttackStage.COLLECTION: 7,
        AttackStage.STAGING: 8,
        AttackStage.PERSISTENCE: 9,
        AttackStage.EXFILTRATION: 10,
        AttackStage.UNKNOWN: 1
    }
    return mapping.get(stage, 1)
