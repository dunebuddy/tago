import json
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from core.models import TagRunResult


runner = CliRunner()


def test_cli_tag_dry_run_json(monkeypatch, tmp_path: Path):
    # bypass AWS identity check
    import core.engine.identity_engine as identity
    monkeypatch.setattr(identity, "get_current_aws_identity", lambda profile=None, region=None: object())

    # fake tag_resources return
    import importlib
    cmd = importlib.import_module("cli.commands.tag")
    fake_result = TagRunResult(
        arn="arn:aws:s3:::b",
        desired_tags={"Owner": "team"},
        existing_tags={"Keep": "yes"},
        final_tags={"Owner": "team", "Keep": "yes"},
        pretty_name="S3 Bucket",
    )
    monkeypatch.setattr(cmd, "tag_resources", lambda **kwargs: [fake_result])

    tpl = tmp_path / "t.yaml"
    tpl.write_text("defaults:\n  Owner: team\n", encoding="utf-8")

    res = runner.invoke(
        app,
        [
            "tag",
            "--arn",
            "arn:aws:s3:::b",
            "--template",
            str(tpl),
            "--dry-run",
            "--output",
            "json",
        ],
    )

    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert "desired" in payload and "existing" in payload and "final" in payload


def test_cli_tag_dry_run_json_multiple_arns(monkeypatch, tmp_path: Path):
    import core.engine.identity_engine as identity
    monkeypatch.setattr(identity, "get_current_aws_identity", lambda profile=None, region=None: object())

    import importlib
    cmd = importlib.import_module("cli.commands.tag")
    fake_results = [
        TagRunResult(
            arn="arn:aws:s3:::a",
            desired_tags={"Owner": "team"},
            existing_tags={},
            final_tags={"Owner": "team"},
            pretty_name="S3 Bucket",
        ),
        TagRunResult(
            arn="arn:aws:s3:::b",
            desired_tags={"Owner": "team"},
            existing_tags={"Keep": "yes"},
            final_tags={"Owner": "team", "Keep": "yes"},
            pretty_name="S3 Bucket",
        ),
    ]
    monkeypatch.setattr(cmd, "tag_resources", lambda **kwargs: fake_results)

    tpl = tmp_path / "t.yaml"
    tpl.write_text("defaults:\n  Owner: team\n", encoding="utf-8")

    res = runner.invoke(
        app,
        [
            "tag",
            "--arn",
            "arn:aws:s3:::a",
            "--arn",
            "arn:aws:s3:::b",
            "--template",
            str(tpl),
            "--dry-run",
            "--output",
            "json",
        ],
    )

    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert "desired" in payload and "existing" in payload and "final" in payload
