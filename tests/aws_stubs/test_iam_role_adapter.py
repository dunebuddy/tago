"""AWS stub tests for IAM role adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.iam_role import IAMRoleTagAdapter
from core.models import TagSet


def test_iam_role_apply_tags_calls_tag_role(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("iam")
    stubber = Stubber(client)

    arn_str = "arn:aws:iam::123456789012:role/MyRole"
    arn = Arn.parse(arn_str)
    role_name = "MyRole"

    stubber.add_response(
        "list_role_tags",
        {"Tags": [{"Key": "Keep", "Value": "yes"}]},
        expected_params={"RoleName": role_name},
    )

    tagset = TagSet.from_dict({"Owner": "team"})
    expected_final = [
        {"Key": "Keep", "Value": "yes"},
        {"Key": "Owner", "Value": "team"},
    ]

    stubber.add_response(
        "tag_role",
        {},
        expected_params={"RoleName": role_name, "Tags": expected_final},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = IAMRoleTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "IAM Role"
    assert result.final_tags == {"Keep": "yes", "Owner": "team"}
