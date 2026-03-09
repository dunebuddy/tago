from pathlib import Path
from typing import Any, Dict, Iterable

from .models import TagSet
from .template_engine import load_and_merge_templates, render_dynamic


def build_tagset(template_paths: str | Path | Iterable[str | Path], overrides: Dict[str, Any]) -> TagSet:
    if isinstance(template_paths, (str, Path)):
        paths = [template_paths]
    else:
        paths = list(template_paths)

    if not paths:
        raise ValueError("At least one template path is required.")

    tpl = load_and_merge_templates(paths)
    merged = render_dynamic(tpl, overrides)
    return TagSet.from_dict(merged)
