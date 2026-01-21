from core.adapters.base import BaseTagAdapter
from core.models import TagSet


class _FakeAdapter(BaseTagAdapter):
    # Not used except to access helper methods.
    service = "x"
    pretty_name = "Fake"

    @classmethod
    def supports(cls, arn):  # pragma: no cover
        return False

    def get_current_tags(self):
        return {"K": "existing", "E": "keep"}

    def apply_tags(self, tagset, dry_run=False, override=False):  # pragma: no cover
        raise NotImplementedError

    def get_context(self):  # pragma: no cover
        return {}


def test_get_aws_tags_safe_mode_preserves_existing_on_conflict(monkeypatch):
    adapter = object.__new__(_FakeAdapter)
    # bypass __init__; we only need get_current_tags + helpers

    tagset = TagSet.from_dict({"K": "desired", "D": "new"})
    desired, existing, final = _FakeAdapter._get_aws_tags(adapter, tagset, override=False)

    final_map = {t["Key"]: t["Value"] for t in final}
    # SAFE: existing wins
    assert final_map["K"] == "existing"
    assert final_map["E"] == "keep"
    assert final_map["D"] == "new"


def test_get_aws_tags_override_mode_desired_wins_on_conflict(monkeypatch):
    adapter = object.__new__(_FakeAdapter)

    tagset = TagSet.from_dict({"K": "desired", "D": "new"})
    desired, existing, final = _FakeAdapter._get_aws_tags(adapter, tagset, override=True)

    final_map = {t["Key"]: t["Value"] for t in final}
    # OVERRIDE: desired wins
    assert final_map["K"] == "desired"
    assert final_map["E"] == "keep"
    assert final_map["D"] == "new"
