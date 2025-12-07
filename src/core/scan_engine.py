# tago/scan_service.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Iterable, Set
from datetime import datetime, timezone
from .template_engine import load_template

from boto3.session import Session
import yaml

from .arn import Arn
from .models import ScanReport, ScanResourceReport
from .adapters import get_adapters_for_service


def _extract_required_keys(template_dict: Dict) -> Set[str]:
    defaults = template_dict.get("defaults", {}) or {}
    dynamics = template_dict.get("dynamics", {}) or {}
    return set(defaults.keys()) | set(dynamics.keys())

def _extract_tag_keys(raw_tags: Any) -> Set[str]:
    """
    Aceita vários formatos de tags e retorna só o set de chaves:
    - dict[str, str]
    - List[{"Key": ..., "Value": ...}]
    - List[Tag] (com atributo .key)
    - None/vazio -> set()
    """
    if not raw_tags:
        return set()

    # Caso S3: dict[str, str]
    if isinstance(raw_tags, dict):
        return set(raw_tags.keys())

    # Caso lista / iterável
    if isinstance(raw_tags, Iterable):
        raw_list = list(raw_tags)
        if not raw_list:
            return set()

        first = raw_list[0]

        # List[{"Key": "X", "Value": "Y"}]
        if isinstance(first, dict) and "Key" in first:
            return {t["Key"] for t in raw_list}

        # List[Tag] com atributo .key
        if hasattr(first, "key"):
            return {t.key for t in raw_list}

    # Se chegar aqui, formato desconhecido
    raise TypeError(f"Formato de tags não suportado: {type(raw_tags)!r}")

def scan_resources(
    service: str,
    service_type: str | None,
    template_path: str,
    profile: str,
    region: str,
) -> ScanReport:
    session = Session(profile_name=profile, region_name=region)

    template_dict = load_template(template_path)
    required_keys = _extract_required_keys(template_dict)
    
    adapter_cls = get_adapters_for_service(service, service_type)

    resources: List[ScanResourceReport] = []

    # garante que o adapter sabe se listar
    if not hasattr(adapter_cls, "list_resources"):
        raise NotImplementedError(f"Adapter {adapter_cls.__name__} does not support listing resources.")

    for arn in adapter_cls.list_resources(session=session):
        adapter = adapter_cls(arn=arn, session=session)

        # aqui uso o que você já tem pra pegar tags atuais
        aws_tags = adapter.get_current_tags()  # List[Dict[Key, Value]] ou List[Tag]

        existing_keys = _extract_tag_keys(aws_tags)

        missing = sorted(required_keys - existing_keys)

        if missing:
            status = "non_compliant"
        else:
            status = "compliant"

        name = getattr(arn, "resource", None) or str(arn)  # adapta ao seu Arn
        arn_str = getattr(arn, "raw", None) or str(arn)  # adapta ao seu Arn

        resources.append(
            ScanResourceReport(
                name=name,
                arn=arn_str,
                adapter=adapter_cls.__name__,
                status=status,
                missing_tags=missing,
            )
        )

    total = len(resources)
    non_compliant = sum(1 for r in resources if r.status == "non_compliant")
    compliant = total - non_compliant

    return ScanReport(
        service=service,
        service_type=service_type,
        checked_at=datetime.now(timezone.utc).isoformat(),
        summary={
            "total_resources": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
        },
        resources=resources,
    )
