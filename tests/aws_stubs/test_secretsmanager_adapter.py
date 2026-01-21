"""AWS stub tests for Secrets Manager adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.secretsmanager_secret import SecretsManagerSecretTagAdapter
from core.models import TagSet


def test_secretsmanager_apply_tags_calls_tag_resource(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("secretsmanager")
    stubber = Stubber(client)

    arn_str = "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret"
    arn = Arn.parse(arn_str)

    stubber.add_response(
        "describe_secret",
        {"Tags": [{"Key": "Keep", "Value": "yes"}]},
        expected_params={"SecretId": arn_str},
    )

    tagset = TagSet.from_dict({"Owner": "team"})
    expected_final = [
        {"Key": "Keep", "Value": "yes"},
        {"Key": "Owner", "Value": "team"},
    ]

    stubber.add_response(
        "tag_resource",
        {},
        expected_params={"SecretId": arn_str, "Tags": expected_final},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = SecretsManagerSecretTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "Secrets Manager Secret"
    assert result.final_tags == {"Keep": "yes", "Owner": "team"}
