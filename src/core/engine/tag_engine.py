import time

from typing import Dict, Any, Iterable
from boto3.session import Session

from ..arn import Arn
from ..merge import build_tagset
from ..adapters import get_adapter_for_arn

def _read_tags_with_retry(
    adapter,
    expected_tagset: Dict[str, str],
    max_attempts: int = 5,
    delay_seconds: float = 0.5,
) -> Dict[str, str]:
    """
    Lê as tags atuais do recurso com retry e backoff.
    expected_tagset = tagset que acabamos de tentar aplicar.
    """
    expected_keys = set(expected_tagset.keys())
    last_tags: Dict[str, str] = {}

    for attempt in range(1, max_attempts + 1):
        current = adapter.get_current_tags()  # chama o adapter puro
        last_tags = current or {}

        # Se já vemos pelo menos todas as chaves que tentamos aplicar, beleza.
        if expected_keys.issubset(last_tags.keys()) or attempt == max_attempts:
            return last_tags

        time.sleep(delay_seconds)
        delay_seconds *= 2  # backoff exponencial

    return last_tags


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
        adapter_cls = get_adapter_for_arn(arn)

        adapter = adapter_cls(arn, session)
        
        adapter_ctx = adapter.get_context()  # ex: {"usage": "storage"}
        ctx: Dict[str, Any] = {**adapter_ctx, **overrides}
        tagset = build_tagset(template_path, ctx)

        adapter.apply_tags(tagset, dry_run=dry_run, override=override)

        return _read_tags_with_retry(adapter, expected_tagset=tagset)