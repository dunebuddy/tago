"""AWS stub tests for EC2 subnet adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.ec2_subnet import EC2SubnetTagAdapter
from core.models import TagSet


def test_ec2_subnet_apply_tags_calls_create_tags(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("ec2")
    stubber = Stubber(client)

    arn_str = "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123"
    arn = Arn.parse(arn_str)
    subnet_id = "subnet-abc123"

    stubber.add_response(
        "describe_tags",
        {"Tags": [{"Key": "Keep", "Value": "yes"}]},
        expected_params={
            "Filters": [{"Name": "resource-id", "Values": [subnet_id]}],
        },
    )

    tagset = TagSet.from_dict({"Owner": "team"})
    expected_final = [
        {"Key": "Keep", "Value": "yes"},
        {"Key": "Owner", "Value": "team"},
    ]

    stubber.add_response(
        "create_tags",
        {},
        expected_params={"Resources": [subnet_id], "Tags": expected_final},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = EC2SubnetTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "EC2 Subnet"
    assert result.final_tags == {"Keep": "yes", "Owner": "team"}
