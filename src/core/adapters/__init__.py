# src/core/adapters/__init__.py
from .base import BaseTagAdapter

import pkgutil
import importlib
from typing import Optional
from boto3.session import Session
from ..arn import Arn


def load_adapters() -> None:
    """
    Garante que todos os módulos de adapters em core.adapters.* foram importados,
    para que o __init_subclass__ do BaseTagAdapter tenha rodado
    e populado o registry.
    """
    # Se já tem coisa registrada, não precisa procurar de novo
    if BaseTagAdapter.registry:
        return

    package_name = __name__  # "core.adapters"

    for finder, name, ispkg in pkgutil.iter_modules(__path__, package_name + "."):
        # evita importar de novo o base ou subpackages estranhos
        if name.endswith(".base"):
            continue
        importlib.import_module(name)


def get_adapter_for_arn(arn: Arn) -> type[BaseTagAdapter]:
    """
    Resolve o adapter correto para um ARN, disparando o auto-discovery
    se o registry ainda estiver vazio.
    """
    load_adapters()

    for adapter_cls in BaseTagAdapter.registry:
        if adapter_cls.supports(arn):
            return adapter_cls

    raise ValueError(f"Nenhum adapter encontrado para ARN: {arn.raw}")

def get_adapters_for_service(service: str, resource_type: str | None)  -> type[BaseTagAdapter]:
    """
    Resolve o adapter correto para um serviço (e opcionalmente tipo de recurso),
    disparando o auto-discovery se o registry ainda estiver vazio.
    """
    load_adapters()

    service = service.lower()
    if resource_type:
        resource_type = resource_type.lower()

    result = []
    for adapter_cls in BaseTagAdapter.registry:
        if adapter_cls.service.lower() != service:
            continue
        if resource_type and (adapter_cls.resource_type or "").lower() != resource_type:
            continue
        return adapter_cls

    raise ValueError(
        f"Nenhum adapter encontrado para o serviço '{service}'"
        f"{f' e o tipo de recurso \'{resource_type}\'' if resource_type else ''}."
    )


