from typing import List, Dict
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet, TagRunResult
from ..arn import Arn


class EC2InstanceTagAdapter(BaseTagAdapter):
    service = "ec2"
    pretty_name = "EC2 Instance"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        # arn:aws:ec2:region:account:instance/i-abc123
        return arn.service == "ec2" and arn.resource.startswith("instance/")
    
    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("ec2")

    def _resource_id(self) -> str:
        # arn:aws:ec2:region:account:instance/i-abc123
        # resource = "instance/i-abc123"
        _, resource_id = self.arn.resource.split("/", 1)
        return resource_id

    def _to_aws_format(self, tagset: TagSet) -> List[Dict[str, str]]:
        return [{"Key": t.key, "Value": t.value} for t in tagset.tags]
    
    def get_context(self) -> Dict[str, str]:
        return {"service_type": "compute"}

    def get_current_tags(self) -> Dict[str, str]:
        """
        Lê as tags atuais da instância EC2 e devolve como dict {key: value},
        igual ao padrão do adapter de S3.
        """
        instance_id = self._resource_id()

        try:
            resp = self.client.describe_tags(
                Filters=[
                    {"Name": "resource-id", "Values": [instance_id]},
                ]
            )
            raw_tags = resp.get("Tags", [])
        except Exception:
            # Em caso de erro inesperado, considera sem tags
            raw_tags = []

        return {t["Key"]: t["Value"] for t in raw_tags}

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> TagRunResult:
        """
        Aplica tags na instância EC2 usando a lógica de merge (_get_aws_tags),
        respeitando o parâmetro override e suportando dry_run.
        """
        instance_id = self._resource_id()

        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)
        desired_map = self._aws_tags_to_dict(desired_tags)
        existing_map = self._aws_tags_to_dict(existing_tags)
        final_map = self._aws_tags_to_dict(final_tags)

        if not dry_run:
            self.client.create_tags(
                Resources=[instance_id],
                Tags=final_tags,
            )

        return TagRunResult(
            arn=self.arn.raw,
            desired_tags=desired_map,
            existing_tags=existing_map,
            final_tags=final_map,
            pretty_name=self.pretty_name,
        )
