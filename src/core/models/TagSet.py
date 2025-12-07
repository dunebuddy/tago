from dataclasses import dataclass
from typing import Dict, List

from .Tag import Tag


@dataclass
class TagSet:
    """
    Representação interna canônica de tags.
    Independente de como cada serviço AWS quer receber essas tags.
    """

    tags: List[Tag]

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "TagSet":
        return cls([Tag(key=k, value=str(v)) for k, v in data.items()])

    def to_dict(self) -> Dict[str, str]:
        return {t.key: t.value for t in self.tags}
