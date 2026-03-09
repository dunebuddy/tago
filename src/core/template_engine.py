from pathlib import Path
from typing import Any, Dict

import yaml
from jinja2 import Environment, StrictUndefined


env = Environment(undefined=StrictUndefined)


def load_template(path: str | Path) -> Dict[str, Any]:
    content = Path(path).read_text(encoding="utf-8")
    # Suporta YAML e JSON (YAML ja e superset)
    return yaml.safe_load(content) or {}


def load_and_merge_templates(paths: list[str | Path]) -> Dict[str, Any]:
    """
    Merge na ordem informada. Em chaves repetidas, o template mais a direita vence,
    mesmo que a chave esteja em seções diferentes (defaults/fixed/dynamic).
    """
    merged_other: Dict[str, Any] = {}
    merged_tags: Dict[str, tuple[str, Any]] = {}
    sections = ("defaults", "fixed", "dynamic")

    for path in paths:
        tpl = load_template(path)
        for section in sections:
            values = tpl.get(section, {}) or {}
            if not isinstance(values, dict):
                continue
            for key, value in values.items():
                merged_tags[key] = (section, value)

        # preserva outras chaves top-level, com precedência à direita
        for key, value in tpl.items():
            if key not in sections:
                merged_other[key] = value

    defaults: Dict[str, Any] = {}
    fixed: Dict[str, Any] = {}
    dynamic: Dict[str, Any] = {}

    for key, (section, value) in merged_tags.items():
        if section == "dynamic":
            dynamic[key] = value
        elif section == "fixed":
            fixed[key] = value
        else:
            defaults[key] = value

    return {
        **merged_other,
        "defaults": defaults,
        "fixed": fixed,
        "dynamic": dynamic,
    }


def render_dynamic(template: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Espera algo como:
    {
        "defaults": {...},
        "fixed": {...},
        "dynamic": {
            "CostCenter": "{{ cost_center }}",
            "Message": "{{ msg }}"
        }
    }
    """
    defaults = template.get("defaults", {}) or {}
    fixed = template.get("fixed", {}) or {}
    dynamic = template.get("dynamic", {}) or {}

    rendered_dynamic: Dict[str, Any] = {}
    for key, expr in dynamic.items():
        template_obj = env.from_string(str(expr))
        rendered_dynamic[key] = template_obj.render(**ctx)

    # ordem: defaults < fixed < dynamic (dynamic ganha)
    merged: Dict[str, Any] = {**defaults, **fixed, **rendered_dynamic}
    return merged
