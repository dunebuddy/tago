"""AWS stub tests for ECR adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.ecr_repository import ECRRepositoryTagAdapter
from core.models import TagSet


def test_ecr_apply_tags_calls_tag_resource(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("ecr")
    stubber = Stubber(client)

    arn_str = "arn:aws:ecr:us-east-1:123456789012:repository/my-repo"
    arn = Arn.parse(arn_str)

    stubber.add_response(
        "list_tags_for_resource",
        {"tags": [{"Key": "Keep", "Value": "yes"}]},
        expected_params={"resourceArn": arn_str},
    )

    tagset = TagSet.from_dict({"Owner": "team"})
    expected_final = [
        {"Key": "Keep", "Value": "yes"},
        {"Key": "Owner", "Value": "team"},
    ]

    stubber.add_response(
        "tag_resource",
        {},
        expected_params={"resourceArn": arn_str, "tags": expected_final},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = ECRRepositoryTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "ECR Repository"
    assert result.final_tags == {"Keep": "yes", "Owner": "team"}
