from typing import Dict, Any, Iterable
from boto3.session import Session
from .arn import Arn
from .merge import build_tagset
from .adapters import get_adapter_for_arn


def tag_resources(
    arns: Iterable[str],
    template_path: str,
    overrides: Dict[str, Any],
    *,
    profile: str | None = None,
    region: str | None = None,
    dry_run: bool = False,
    override: bool = False,
) -> None:
    session = Session(profile_name=profile, region_name=region)


    for arn_str in arns:
        arn = Arn.parse(arn_str)
        adapter = get_adapter_for_arn(arn, session)
        
        adapter_ctx = adapter.get_context()  # ex: {"usage": "storage"}
        ctx: Dict[str, Any] = {**adapter_ctx, **overrides}
        tagset = build_tagset(template_path, ctx)

        adapter.apply_tags(tagset, dry_run=dry_run, override=override)
