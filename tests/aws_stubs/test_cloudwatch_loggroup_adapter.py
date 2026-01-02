"""AWS stub tests for CloudWatch log group adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.cloudwatch_loggroup import CloudWatchLogGroupTagAdapter
from core.models import TagSet


def test_cloudwatch_loggroup_apply_tags_calls_tag_log_group(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("logs")
    stubber = Stubber(client)

    arn_str = "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/my-func:*"
    arn = Arn.parse(arn_str)
    log_group_name = "/aws/lambda/my-func"

    stubber.add_response(
        "list_tags_log_group",
        {"tags": {"Keep": "yes"}},
        expected_params={"logGroupName": log_group_name},
    )

    tagset = TagSet.from_dict({"Owner": "team"})

    stubber.add_response(
        "tag_log_group",
        {},
        expected_params={
            "logGroupName": log_group_name,
            "tags": {"Keep": "yes", "Owner": "team"},
        },
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = CloudWatchLogGroupTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "CloudWatch Log Group"
    assert result.final_tags == {"Keep": "yes", "Owner": "team"}
