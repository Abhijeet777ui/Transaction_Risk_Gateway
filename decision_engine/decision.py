from enum import Enum

class Decision(Enum):
    ALLOW = "allow"
    REQUIRE_VERIFICATION = "require_verification"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    LOCK_ACCOUNT = "lock_account"
