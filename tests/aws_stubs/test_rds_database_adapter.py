"""AWS stub tests for RDS database adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.rds_database import RDSDatabaseTagAdapter
from core.models import TagSet


def test_rds_database_apply_tags_calls_add_tags_to_resource(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("rds")
    stubber = Stubber(client)

    arn_str = "arn:aws:rds:us-east-1:123456789012:db:my-database"
    arn = Arn.parse(arn_str)

    stubber.add_response(
        "list_tags_for_resource",
        {"TagList": [{"Key": "Keep", "Value": "yes"}]},
        expected_params={"ResourceName": arn_str},
    )

    tagset = TagSet.from_dict({"Owner": "team"})
    expected_final = [
        {"Key": "Keep", "Value": "yes"},
        {"Key": "Owner", "Value": "team"},
    ]

    stubber.add_response(
        "add_tags_to_resource",
        {},
        expected_params={"ResourceName": arn_str, "Tags": expected_final},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = RDSDatabaseTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "RDS Database"
    assert result.final_tags == {"Keep": "yes", "Owner": "team"}
