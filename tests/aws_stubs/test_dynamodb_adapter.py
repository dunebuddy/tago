"""AWS stub tests for DynamoDB adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.dynamodb_table import DynamoDBTableTagAdapter
from core.models import TagSet


def test_dynamodb_apply_tags_calls_tag_resource(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("dynamodb")
    stubber = Stubber(client)

    arn_str = "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
    arn = Arn.parse(arn_str)

    stubber.add_response(
        "list_tags_of_resource",
        {"Tags": [{"Key": "Keep", "Value": "yes"}]},
        expected_params={"ResourceArn": arn_str},
    )

    tagset = TagSet.from_dict({"Owner": "team"})
    expected_final = [
        {"Key": "Keep", "Value": "yes"},
        {"Key": "Owner", "Value": "team"},
    ]

    stubber.add_response(
        "tag_resource",
        {},
        expected_params={"ResourceArn": arn_str, "Tags": expected_final},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = DynamoDBTableTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "DynamoDB Table"
    assert result.final_tags == {"Keep": "yes", "Owner": "team"}
