from typing import Dict, List
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet
from ..arn import Arn


class DynamoDBTableTagAdapter(BaseTagAdapter):
    service = "dynamodb"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        """
        Suporta ARNs de tabela DynamoDB, ex:
        arn:aws:dynamodb:sa-east-1:123456789012:table/MinhaTabela
        """
        return arn.service == "dynamodb" and arn.resource.startswith("table/")

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("dynamodb")

    def get_context(self) -> Dict[str, str]:
        """
        Contexto específico para DynamoDB.
        """
        return {
            "service_type": "database",
        }

    def get_current_tags(self) -> Dict[str, str]:
        """
        DynamoDB retorna tags via ListTagsOfResource.
        Convertido aqui para Dict[str, str] como no padrão do S3 adapter.
        """
        resource_arn = self.arn.raw

        try:
            resp = self.client.list_tags_of_resource(ResourceArn=resource_arn)
            raw_tags = resp.get("Tags", [])
        except self.client.exceptions.ResourceNotFoundException:
            raw_tags = []
        except Exception:
            # Em caso de erro inesperado, considera sem tags (comportamento igual ao do S3)
            raw_tags = []

        return {t["Key"]: t["Value"] for t in raw_tags}

    def apply_tags(self, tagset: TagSet, dry_run: bool = False, override: bool = False) -> None:
        """
        Aplica tags usando o pipeline de merge e o formato AWS.
        """
        resource_arn = self.arn.raw

        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if dry_run:
            self._print_dry_run(
                desired_tags,
                existing_tags,
                final_tags,
                "DynamoDB Table",
                override,
            )
            return

        self.client.tag_resource(
            ResourceArn=resource_arn,
            Tags=final_tags,
        )
