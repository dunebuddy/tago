import json
from typing import Optional

import typer
import typer_di
import yaml

from core.adapters import load_adapters
from core.adapters.base import BaseTagAdapter

from .console import BOLD, CYAN, GREEN, GREY, RESET
from ..params import output_params


def _print_adapters(adapters_list: list[dict[str, Optional[str]]], output: str) -> None:
    if output == "json":
        typer.echo(json.dumps(adapters_list, indent=2, ensure_ascii=False))
        return

    if output == "yaml":
        typer.echo(yaml.safe_dump(adapters_list, sort_keys=False, allow_unicode=True))
        return

    print()
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print(f"{CYAN}{BOLD}Registered Adapters:{RESET}")
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print()
    if not BaseTagAdapter.registry:
        print("  (none registered)")
        print()
        return

    for adapter in adapters_list:
        name = adapter["name"]
        service = adapter["service"]
        resource_type = adapter["resource_type"]

        meta_parts = []
        if service:
            meta_parts.append(f"service={service}")
        if resource_type:
            meta_parts.append(f"resource_type={resource_type}")

        if meta_parts:
            meta = ", ".join(meta_parts)
            print(f"  {GREEN}•{RESET} {name:<40} {GREY}({meta}){RESET}")
        else:
            print(f"  {GREEN}•{RESET} {name}")

    print()
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print()


def adapters(output: str = typer_di.Depends(output_params)) -> None:
    """
    Lista todos os adapters registrados no Tago.

    Garante o carregamento dos módulos e imprime a tabela no stdout.
    """
    # Garante que todos os módulos de adapters foram importados
    load_adapters()

    adapters_list = []
    for adapter in sorted(BaseTagAdapter.registry, key=lambda c: c.__name__.lower()):
        adapters_list.append(
            {
                "name": adapter.__name__,
                "service": getattr(adapter, "service", None),
                "resource_type": getattr(adapter, "resource_type", None),
            }
        )

    _print_adapters(adapters_list, output)

    
