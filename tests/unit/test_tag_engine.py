from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.models import TagSet, TagRunResult
from core.engine import tag_engine


class _RetryAdapter:
    def __init__(self, snapshots):
        self._it = iter(snapshots)

    def get_current_tags(self):
        try:
            return next(self._it)
        except StopIteration:
            return {}


def test_read_tags_with_retry_stops_when_expected_keys_present(monkeypatch):
    # avoid sleeping in tests
    monkeypatch.setattr(tag_engine.time, "sleep", lambda _: None)

    expected = TagSet.from_dict({"A": "1", "B": "2"})
    adapter = _RetryAdapter([
        {"A": "1"},
        {"A": "1", "B": "2"},
        {"A": "1", "B": "2", "C": "3"},
    ])

    out = tag_engine._read_tags_with_retry(adapter, expected, max_attempts=5, delay_seconds=0)
    assert out == {"A": "1", "B": "2"}


class _FakeArn:
    def __init__(self, raw: str):
        self.raw = raw
        self.service = "fake"
        self.resource = "x"

    @classmethod
    def parse(cls, s: str):
        return cls(s)


class _FakeAdapterImpl:
    def __init__(self, arn, session):
        self.arn = arn
        self.session = session
        self._tags = {"Keep": "yes"}

    def get_context(self):
        return {"service_type": "test"}

    def get_current_tags(self):
        return dict(self._tags)

    def apply_tags(self, tagset: TagSet, dry_run: bool = False, override: bool = False) -> TagRunResult:
        desired = dict(tagset.to_dict())
        existing = dict(self._tags)

        if not override:
            final = {**desired, **self._tags}
        else:
            final = {**self._tags, **desired}

        if not dry_run:
            # simulate that AWS eventually reflects final tags
            self._tags = dict(final)

        return TagRunResult(
            arn=self.arn.raw,
            desired_tags=desired,
            existing_tags=existing,
            final_tags=final,
            pretty_name="Fake",
        )


def test_tag_resources_sets_applied_tags_in_non_dry_run(monkeypatch, tmp_path):
    # patch parsing + adapter resolution
    monkeypatch.setattr(tag_engine, "Arn", _FakeArn)
    monkeypatch.setattr(tag_engine, "get_adapter_for_arn", lambda arn: _FakeAdapterImpl)
    monkeypatch.setattr(tag_engine.time, "sleep", lambda _: None)

    # tiny template file
    tpl = tmp_path / "t.yaml"
    tpl.write_text("defaults:\n  Owner: team\n", encoding="utf-8")

    results = tag_engine.tag_resources(
        arns=["arn:fake"],
        template_path=str(tpl),
        overrides={},
        profile=None,
        region="us-east-1",
        dry_run=False,
        override=True,
    )

    assert len(results) == 1
    r = results[0]
    assert r.applied_tags is not None
    assert r.applied_tags["Owner"] == "team"


def test_tag_resources_dry_run_does_not_set_applied_tags(monkeypatch, tmp_path):
    monkeypatch.setattr(tag_engine, "Arn", _FakeArn)
    monkeypatch.setattr(tag_engine, "get_adapter_for_arn", lambda arn: _FakeAdapterImpl)

    tpl = tmp_path / "t.yaml"
    tpl.write_text("defaults:\n  Owner: team\n", encoding="utf-8")

    results = tag_engine.tag_resources(
        arns=["arn:fake"],
        template_path=str(tpl),
        overrides={},
        profile=None,
        region="us-east-1",
        dry_run=True,
        override=True,
    )
    assert results[0].applied_tags is None


def test_tag_resources_returns_results_for_multiple_arns(monkeypatch, tmp_path):
    monkeypatch.setattr(tag_engine, "Arn", _FakeArn)
    monkeypatch.setattr(tag_engine, "get_adapter_for_arn", lambda arn: _FakeAdapterImpl)

    tpl = tmp_path / "t.yaml"
    tpl.write_text("defaults:\n  Owner: team\n", encoding="utf-8")

    results = tag_engine.tag_resources(
        arns=["arn:fake:1", "arn:fake:2"],
        template_path=str(tpl),
        overrides={},
        profile=None,
        region="us-east-1",
        dry_run=True,
        override=False,
    )

    assert len(results) == 2
    assert [r.arn for r in results] == ["arn:fake:1", "arn:fake:2"]
