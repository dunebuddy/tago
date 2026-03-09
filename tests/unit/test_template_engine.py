from pathlib import Path

import pytest

from core.template_engine import load_and_merge_templates, render_dynamic
from core.merge import build_tagset


def test_render_dynamic_merges_defaults_fixed_dynamic_precedence():
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


def test_render_dynamic_missing_var_raises():
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


def test_load_and_merge_templates_right_precedence(tmp_path: Path):
    t1 = tmp_path / "t1.yaml"
    t2 = tmp_path / "t2.yaml"
    t3 = tmp_path / "t3.yaml"

    t1.write_text(
        """
defaults:
  Owner: team-a
dynamic:
  Name: "{{ app }}"
""",
        encoding="utf-8",
    )
    t2.write_text(
        """
defaults:
  Owner: team-b
fixed:
  Env: hml
""",
        encoding="utf-8",
    )
    t3.write_text(
        """
dynamic:
  Name: fixed-name
""",
        encoding="utf-8",
    )

    merged = load_and_merge_templates([str(t1), str(t2), str(t3)])
    out = render_dynamic(merged, {})
    assert out == {"Owner": "team-b", "Env": "hml", "Name": "fixed-name"}


def test_load_and_merge_templates_overrides_dynamic_with_later_default(tmp_path: Path):
    base = tmp_path / "base.yaml"
    env = tmp_path / "env.yaml"

    base.write_text(
        """
dynamic:
  Environment: "{{ environment }}"
""",
        encoding="utf-8",
    )
    env.write_text(
        """
defaults:
  Environment: "dev"
""",
        encoding="utf-8",
    )

    merged = load_and_merge_templates([str(base), str(env)])
    out = render_dynamic(merged, {})
    assert out["Environment"] == "dev"
