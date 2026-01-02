from dataclasses import dataclass
from typing import Dict, List, Optional

from core.arn import Arn


@dataclass
class TagRunResult:
    """
    Resultado de um apply_tags, independente de dry-run.
    """

    arn: Arn
    desired_tags: List[Dict[str, str]]
    existing_tags: List[Dict[str, str]]
    final_tags: List[Dict[str, str]]
    pretty_name: str
    applied_tags: Optional[Dict[str, str]] = None
