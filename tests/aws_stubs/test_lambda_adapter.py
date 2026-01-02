"""AWS stub tests for Lambda adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.lambda_function import LambdaFunctionTagAdapter
from core.models import TagSet


def test_lambda_apply_tags_calls_tag_resource_with_dict(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("lambda")
    stubber = Stubber(client)

    arn_str = "arn:aws:lambda:us-east-1:123456789012:function:my-func"
    arn = Arn.parse(arn_str)

    # existing tags
    stubber.add_response(
        "list_tags",
        {"Tags": {"Keep": "yes"}},
        expected_params={"Resource": arn_str},
    )

    tagset = TagSet.from_dict({"Owner": "team"})
    # override=True means desired wins; final should include Keep + Owner
    stubber.add_response(
        "tag_resource",
        {},
        expected_params={"Resource": arn_str, "Tags": {"Keep": "yes", "Owner": "team"}},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = LambdaFunctionTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.final_tags["Owner"] == "team"
