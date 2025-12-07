from typing import Dict, Iterable, List
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet
from ..arn import Arn


class ECRRepositoryTagAdapter(BaseTagAdapter):
    service = "ecr"
    resource_type = "repository"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        """
        Suporta ARNs de repositório ECR, ex:
        arn:aws:ecr:sa-east-1:123456789012:repository/meu-repo
        """
        return arn.service == "ecr" and arn.resource.startswith("repository/")
    
    @classmethod
    def list_resources(cls, session: Session) -> Iterable[Arn]:
        client = session.client("ecr")
        paginator = client.get_paginator("describe_repositories")

        for page in paginator.paginate():
            for repo in page.get("repositories", []):
                # describe_repositories retorna 'repositoryArn'
                yield Arn.parse(repo["repositoryArn"])

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("ecr")

    def get_context(self) -> Dict[str, str]:
        return {
            "service_type": "container-registry",
        }

    def get_current_tags(self) -> Dict[str, str]:
        """
        Obtém as tags atuais do repositório ECR e retorna como dict {key: value}.
        """
        resource_arn = self.arn.raw

        try:
            resp = self.client.list_tags_for_resource(
                resourceArn=resource_arn
            )
            raw_tags = resp.get("tags", [])
        except Exception:
            # Em caso de qualquer erro inesperado, assume sem tags.
            raw_tags = []

        return {t["Key"]: t["Value"] for t in raw_tags}

    def _to_aws_format(self, tagset: TagSet) -> List[Dict[str, str]]:
        """
        ECR usa o formato clássico de lista [{Key, Value}].
        """
        return [{"Key": t.key, "Value": t.value} for t in tagset.tags]

    def apply_tags(self, tagset: TagSet, dry_run: bool = False, override: bool = False) -> None:
        resource_arn = self.arn.raw

        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if dry_run:
            self._print_dry_run(
                desired_tags,
                existing_tags,
                final_tags,
                "ECR Repository",
                override,
            )
            return

        self.client.tag_resource(
            resourceArn=resource_arn,
            tags=final_tags,
        )
