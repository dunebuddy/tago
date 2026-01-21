from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TagRunResult:
    """
    Resultado de um apply_tags, independente de dry-run.
    """

    arn: str
    desired_tags: Dict[str, str]
    existing_tags: Dict[str, str]
    final_tags: Dict[str, str]
    pretty_name: str
    applied_tags: Optional[Dict[str, str]] = None
