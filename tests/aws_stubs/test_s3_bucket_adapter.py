"""AWS stub tests for S3 bucket adapter tagging behavior."""

import boto3
from botocore.stub import Stubber
from botocore.exceptions import ClientError

from core.arn import Arn
from core.adapters.s3_bucket import S3BucketTagAdapter
from core.models import TagSet


def test_s3_get_current_tags_returns_empty_on_no_such_tagset(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("s3")
    stubber = Stubber(client)

    bucket = "my-bucket"
    arn = Arn.parse(f"arn:aws:s3:::{bucket}")

    err = ClientError(
        {"Error": {"Code": "NoSuchTagSet", "Message": "The TagSet does not exist"}},
        "GetBucketTagging",
    )
    stubber.add_client_error("get_bucket_tagging", service_error_code="NoSuchTagSet", service_message="...", http_status_code=404, expected_params={"Bucket": bucket})

    # força o adapter a usar nosso client stubado
    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = S3BucketTagAdapter(arn, session)
        tags = adapter.get_current_tags()

    assert tags == {}


def test_s3_apply_tags_calls_put_bucket_tagging(monkeypatch):
    session = boto3.session.Session(region_name="us-east-1")
    client = session.client("s3")
    stubber = Stubber(client)

    bucket = "my-bucket"
    arn = Arn.parse(f"arn:aws:s3:::{bucket}")

    # existing tags: empty
    stubber.add_client_error(
        "get_bucket_tagging",
        service_error_code="NoSuchTagSet",
        service_message="The TagSet does not exist",
        http_status_code=404,
        expected_params={"Bucket": bucket},
    )

    tagset = TagSet.from_dict({"Owner": "team", "Env": "hml"})
    expected_final = [
        {"Key": "Owner", "Value": "team"},
        {"Key": "Env", "Value": "hml"},
    ]

    stubber.add_response(
        "put_bucket_tagging",
        {},
        expected_params={"Bucket": bucket, "Tagging": {"TagSet": expected_final}},
    )

    monkeypatch.setattr(session, "client", lambda name: client)

    with stubber:
        adapter = S3BucketTagAdapter(arn, session)
        result = adapter.apply_tags(tagset, dry_run=False, override=True)

    assert result.pretty_name == "S3 Bucket"
    assert result.final_tags == {"Owner": "team", "Env": "hml"}
