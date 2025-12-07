from pathlib import Path
from typing import Any, Dict
import yaml
from jinja2 import Environment, StrictUndefined


env = Environment(undefined=StrictUndefined)


def load_template(path: str | Path) -> Dict[str, Any]:
    content = Path(path).read_text(encoding="utf-8")
    # Suporta YAML e JSON (YAML já é superset)
    return yaml.safe_load(content)


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
        # expr é uma string Jinja2
        template_obj = env.from_string(str(expr))
        rendered_dynamic[key] = template_obj.render(**ctx)

    # ordem: defaults < fixed < dynamic (dynamic ganha)
    merged: Dict[str, Any] = {**defaults, **fixed, **rendered_dynamic}
    return merged
