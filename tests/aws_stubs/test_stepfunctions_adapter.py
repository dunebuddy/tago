"""AWS stub tests for Step Functions adapter tagging behavior."""

import boto3
from botocore.stub import Stubber

from core.arn import Arn
from core.adapters.stepfunctions_stateMachine import StepFunctionsStateMachineTagAdapter
from core.models import TagSet


def test_stepfunctions_apply_tags_calls_tag_resource(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("stepfunctions")
    stubber = Stubber(client)

    arn_str = "arn:aws:states:us-east-1:123456789012:stateMachine:my-machine"
    arn = Arn.parse(arn_str)

    stubber.add_response(
        "list_tags_for_resource",
        {"tags": [{"key": "Keep", "value": "yes"}]},
        expected_params={"resourceArn": arn_str},
    )

    tagset = TagSet.from_dict({"Owner": "team"})
    expected_sf_tags = [
        {"key": "Keep", "value": "yes"},
        {"key": "Owner", "value": "team"},
    ]

    stubber.add_response(
        "tag_resource",
        {},
        expected_params={"resourceArn": arn_str, "tags": expected_sf_tags},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = StepFunctionsStateMachineTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "Step Functions State Machine"
    assert result.final_tags == {"Keep": "yes", "Owner": "team"}
