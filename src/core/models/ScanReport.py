import yaml

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ScanResourceReport:
    name: str
    arn: str
    adapter: str
    status: str  # 'compliant' | 'non_compliant'
    missing_tags: List[str]


@dataclass
class ScanReport:
    service: str
    service_type: str | None
    checked_at: str
    summary: Dict[str, int]
    resources: List[ScanResourceReport]

    def to_yaml(self) -> str:
        doc = {
            "service": self.service,
            **({"service_type": self.service_type} if self.service_type else {}),
            "checked_at": self.checked_at,
            "summary": self.summary,
            "resources": [
                {
                    "name": r.name,
                    "arn": r.arn,
                    "adapter": r.adapter,
                    "status": r.status,
                    **({"missing_tags": r.missing_tags} if r.missing_tags else {}),
                }
                for r in self.resources
            ],
        }
        return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)