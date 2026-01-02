from pathlib import Path

import pytest

from core.template_engine import load_template, render_dynamic
from core.merge import build_tagset


def test_render_dynamic_merges_defaults_fixed_dynamic_precedence(tmp_path: Path):
    tpl = {
        "defaults": {"Owner": "defaults", "Env": "dev"},
        "fixed": {"Owner": "fixed", "CostCenter": "123"},
        "dynamic": {"Owner": "{{ owner }}", "Message": "{{ msg }}"},
    }

    out = render_dynamic(tpl, {"owner": "dynamic", "msg": "hello"})
    # dynamic ganha de fixed e defaults
    assert out["Owner"] == "dynamic"
    # fixed ganha de defaults
    assert out["CostCenter"] == "123"
    assert out["Env"] == "dev"
    assert out["Message"] == "hello"


def test_render_dynamic_strict_undefined_raises():
    tpl = {"dynamic": {"Owner": "{{ missing_var }}"}}
    with pytest.raises(Exception):
        render_dynamic(tpl, {})


def test_build_tagset_from_template_file(tmp_path: Path):
    p = tmp_path / "t.yaml"
    p.write_text(
        """
defaults:
  Owner: "team"
dynamic:
  Env: "{{ env }}"
""",
        encoding="utf-8",
    )

    tagset = build_tagset(str(p), {"env": "hml"})
    as_dict = tagset.to_dict()
    assert as_dict == {"Owner": "team", "Env": "hml"}
