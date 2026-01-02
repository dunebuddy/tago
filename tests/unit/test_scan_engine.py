from __future__ import annotations

from dataclasses import dataclass

from core.engine import scan_engine


def test_extract_required_keys_includes_dynamic_keys():
    tpl = {"defaults": {"A": "1"}, "dynamic": {"B": "{{ b }}"}}
    assert scan_engine._extract_required_keys(tpl) == {"A", "B"}


class _FakeArn:
    def __init__(self, raw):
        self.raw = raw
        self.resource = raw


class _FakeAdapter:
    service = "s"
    resource_type = "t"

    @classmethod
    def list_resources(cls, session):
        yield _FakeArn("arn:1")
        yield _FakeArn("arn:2")

    def __init__(self, arn, session):
        self.arn = arn

    def get_current_tags(self):
        if self.arn.raw == "arn:1":
            return {"A": "1"}
        return {"A": "1", "B": "2"}


def test_scan_resources_marks_missing_tags(monkeypatch, tmp_path):
    # template requiring A+B
    tpl = tmp_path / "t.yaml"
    tpl.write_text("defaults:\n  A: 1\ndynamic:\n  B: '{{ b }}'\n", encoding="utf-8")

    monkeypatch.setattr(scan_engine, "get_adapters_for_service", lambda service, service_type: _FakeAdapter)
    # avoid needing AWS session auth in unit test
    monkeypatch.setattr(scan_engine, "Session", lambda profile_name, region_name: object())

    report = scan_engine.scan_resources(
        service="s",
        service_type="t",
        template_path=str(tpl),
        profile="p",
        region="us-east-1",
    )

    assert report.summary["total_resources"] == 2
    non = [r for r in report.resources if r.status == "non_compliant"]
    assert len(non) == 1
    assert non[0].arn == "arn:1"
    assert non[0].missing_tags == ["B"]
