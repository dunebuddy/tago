import time

from typing import Dict, Any, Iterable
from boto3.session import Session

from ..arn import Arn
from ..merge import build_tagset
from ..models import TagSet
from ..adapters import get_adapter_for_arn

def _read_tags_with_retry(
    adapter,
    expected_tagset: TagSet,
    max_attempts: int = 5,
    delay_seconds: float = 0.5,
) -> Dict[str, str]:
    """
    Lê as tags atuais do recurso com retry e backoff.
    expected_tagset é um TagSet (não um dict).

    - expected_tagset: TagSet com Tag(key, value)
    - adapter.get_current_tags(): Dict[str, str]
    - Retorna: Dict[str, str] com as tags lidas da AWS (ou último valor lido)
    """

    # 1) extrai as chaves esperadas a partir do TagSet
    expected_keys = {t.key for t in expected_tagset.tags}

    last_tags: Dict[str, str] = {}

    for attempt in range(1, max_attempts + 1):
        # 2) lê as tags atuais do adapter (sempre dict[str, str])
        current = adapter.get_current_tags() or {}
        last_tags = current

        current_keys = set(current.keys())

        # 3) se todas as keys esperadas já aparecem, ou acabou o número de tentativas, devolve
        if expected_keys.issubset(current_keys) or attempt == max_attempts:
            return current

        # 4) ainda não bateu, espera e tenta de novo (backoff exponencial)
        time.sleep(delay_seconds)
        delay_seconds *= 2

    # Se nunca bater o subset, devolve a última leitura
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