"""AWS stub tests for identity engine STS caller identity behavior."""

import boto3
from botocore.stub import Stubber

from core.engine import identity_engine


def test_get_current_aws_identity_uses_sts(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    sts = session.client("sts")
    stubber = Stubber(sts)

    stubber.add_response(
        "get_caller_identity",
        {"Account": "123", "Arn": "arn:aws:sts::123:assumed-role/x/y", "UserId": "U"},
        expected_params={},
    )

    # Patch boto3.session.Session constructor used inside identity_engine
    class _FakeSession:
        def __init__(self, profile_name=None, region_name=None):
            self.profile_name = profile_name
            self.region_name = region_name

        def client(self, name):
            assert name == "sts"
            return sts

    monkeypatch.setattr(identity_engine.boto3.session, "Session", _FakeSession)

    with stubber:
        ident = identity_engine.get_current_aws_identity(profile="p", region="us-east-1")

    assert ident.account == "123"
    assert ident.profile == "p"
    assert ident.region == "us-east-1"
