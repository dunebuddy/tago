from typing import Dict, Iterable
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet, TagRunResult
from ..arn import Arn


class EC2SecurityGroupTagAdapter(BaseTagAdapter):
    service = "ec2"
    resource_type = "security-groups"
    pretty_name = "EC2 Security Group"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        # arn:aws:ec2:region:account:security-group/sg-abc123
        return arn.service == "ec2" and arn.resource.startswith("security-group/")

    @classmethod
    def list_resources(cls, session: Session) -> Iterable[Arn]:
        client = session.client("ec2")
        paginator = client.get_paginator("describe_security_groups")
        for page in paginator.paginate():
            for sg in page.get("SecurityGroups", []):
                group_id = sg["GroupId"]
                region = session.region_name or ""
                account_id = sg.get("OwnerId", "")
                yield Arn.parse(
                    f"arn:aws:ec2:{region}:{account_id}:security-group/{group_id}"
                )

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("ec2")

    def _resource_id(self) -> str:
        # resource = "security-group/sg-abc123"
        _, group_id = self.arn.resource.split("/", 1)
        return group_id

    def get_context(self) -> Dict[str, str]:
        return {"service_type": "network"}

    def get_current_tags(self) -> Dict[str, str]:
        group_id = self._resource_id()

        try:
            resp = self.client.describe_tags(
                Filters=[
                    {"Name": "resource-id", "Values": [group_id]},
                ]
            )
            raw_tags = resp.get("Tags", [])
        except Exception:
            raw_tags = []

        return {t["Key"]: t["Value"] for t in raw_tags}

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> TagRunResult:
        group_id = self._resource_id()

        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)
        desired_map = self._aws_tags_to_dict(desired_tags)
        existing_map = self._aws_tags_to_dict(existing_tags)
        final_map = self._aws_tags_to_dict(final_tags)

        if not dry_run:
            self.client.create_tags(
                Resources=[group_id],
                Tags=final_tags,
            )

        return TagRunResult(
            arn=self.arn.raw,
            desired_tags=desired_map,
            existing_tags=existing_map,
            final_tags=final_map,
            pretty_name=self.pretty_name,
        )
