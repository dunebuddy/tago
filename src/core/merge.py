from typing import Dict, Any
from .models import TagSet
from .template_engine import load_template, render_dynamic


def build_tagset(template_path: str, overrides: Dict[str, Any]) -> TagSet:
    tpl = load_template(template_path)
    merged = render_dynamic(tpl, overrides)
    return TagSet.from_dict(merged)
