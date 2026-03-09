from typing import Dict, Iterable
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet, TagRunResult
from ..arn import Arn


class RDSSubnetGroupTagAdapter(BaseTagAdapter):
    service = "rds"
    resource_type = "subnet-groups"
    pretty_name = "RDS Subnet Group"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        # arn:aws:rds:region:account:subgrp:my-subnet-group
        return arn.service == "rds" and arn.resource.startswith("subgrp:")

    @classmethod
    def list_resources(cls, session: Session) -> Iterable[Arn]:
        client = session.client("rds")
        paginator = client.get_paginator("describe_db_subnet_groups")
        for page in paginator.paginate():
            for subnet_group in page.get("DBSubnetGroups", []):
                subnet_group_arn = subnet_group.get("DBSubnetGroupArn")
                if subnet_group_arn:
                    yield Arn.parse(subnet_group_arn)

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("rds")

    def get_context(self) -> Dict[str, str]:
        return {"service_type": "database"}

    def get_current_tags(self) -> Dict[str, str]:
        try:
            resp = self.client.list_tags_for_resource(ResourceName=self.arn.raw)
            raw_tags = resp.get("TagList", [])
        except self.client.exceptions.DBSubnetGroupNotFoundFault:
            raw_tags = []
        except Exception:
            raw_tags = []

        return {t["Key"]: t["Value"] for t in raw_tags}

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> TagRunResult:
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)
        desired_map = self._aws_tags_to_dict(desired_tags)
        existing_map = self._aws_tags_to_dict(existing_tags)
        final_map = self._aws_tags_to_dict(final_tags)

        if not dry_run:
            self.client.add_tags_to_resource(
                ResourceName=self.arn.raw,
                Tags=final_tags,
            )

        return TagRunResult(
            arn=self.arn.raw,
            desired_tags=desired_map,
            existing_tags=existing_map,
            final_tags=final_map,
            pretty_name=self.pretty_name,
        )
