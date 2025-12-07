from dataclasses import dataclass
from typing import Optional

@dataclass
class AwsIdentity:
    account: str
    arn: str
    user_id: str
    region: Optional[str]
    profile: Optional[str]

class AwsIdentityError(RuntimeError):
    pass