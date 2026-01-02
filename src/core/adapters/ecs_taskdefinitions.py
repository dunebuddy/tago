from typing import Dict, List
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet, TagRunResult
from ..arn import Arn


class ECSTaskDefinitionTagAdapter(BaseTagAdapter):
    """
    Adapter para aplicar tags em ECS Task Definitions.

    Exemplo de ARN suportado:
      arn:aws:ecs:sa-east-1:123456789012:task-definition/meu-task:1
    """
    service = "ecs"
    pretty_name = "ECS Task Definition"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        # arn:aws:ecs:region:account:task-definition/family:revision
        return arn.service == "ecs" and arn.resource.startswith("task-definition/")

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("ecs")

    def get_context(self) -> Dict[str, str]:
        return {
            "service_type": "compute",
            "resource_type": "ecs-task-definition",
        }

    def _to_ecs_format(self, tags: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Converte [{Key, Value}] para o formato de ECS:
        [{ "key": ..., "value": ... }].
        """
        return [{"key": t["Key"], "value": t["Value"]} for t in tags]

    def get_current_tags(self) -> Dict[str, str]:
        """
        Lê as tags atuais da Task Definition e retorna como {key: value}.
        ECS usa 'tags': [{'key', 'value'}].
        """
        resource_arn = self.arn.raw

        try:
            resp = self.client.list_tags_for_resource(resourceArn=resource_arn)
            raw_tags = resp.get("tags", [])
        except Exception:
            raw_tags = []

        return {t["key"]: t["value"] for t in raw_tags}

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> TagRunResult:
        resource_arn = self.arn.raw

        # Sempre em formato [{Key, Value}]
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if not dry_run:
            ecs_tags = self._to_ecs_format(final_tags)

            self.client.tag_resource(
                resourceArn=resource_arn,
                tags=ecs_tags,
            )

        return TagRunResult(
            arn=self.arn,
            desired_tags=desired_tags,
            existing_tags=existing_tags,
            final_tags=final_tags,
            pretty_name=self.pretty_name,
        )
