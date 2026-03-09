from typing import Dict, Iterable
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet, TagRunResult
from ..arn import Arn


class RDSDatabaseTagAdapter(BaseTagAdapter):
    service = "rds"
    resource_type = "databases"
    pretty_name = "RDS Database"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        # arn:aws:rds:region:account:db:my-database
        return arn.service == "rds" and arn.resource.startswith("db:")

    @classmethod
    def list_resources(cls, session: Session) -> Iterable[Arn]:
        client = session.client("rds")
        paginator = client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                db_arn = db.get("DBInstanceArn")
                if db_arn:
                    yield Arn.parse(db_arn)

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("rds")

    def get_context(self) -> Dict[str, str]:
        return {"service_type": "database"}

    def get_current_tags(self) -> Dict[str, str]:
        try:
            resp = self.client.list_tags_for_resource(ResourceName=self.arn.raw)
            raw_tags = resp.get("TagList", [])
        except self.client.exceptions.DBInstanceNotFoundFault:
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
