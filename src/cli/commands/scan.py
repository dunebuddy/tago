from pathlib import Path
from typing import Optional

import typer

from core.engine.identity_engine import requires_aws_identity
from core.engine.scan_engine import scan_resources

from .console import BOLD, CYAN, GREEN, GREY, RESET


@requires_aws_identity
def scan(
    service: str = typer.Argument(
        ...,
        help="Serviço AWS (ex.: s3, lambda, states).",
    ),
    service_type: Optional[str] = typer.Argument(
        None,
        help="Tipo de Serviço (ex.: functions, layers, buckets). Opcional.",
    ),
    template: Path = typer.Option(
        ...,
        "--template",
        "-t",
        help="Template de tags do Tago (YAML).",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output da operação (YAML).",
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        help="AWS profile name (from ~/.aws/config).",
    ),
    region: Optional[str] = typer.Option(
        None,
        "--region",
        help="AWS region, e.g. sa-east-1.",
    ),
) -> None:
    """
    Varre recursos de um serviço (e opcionalmente subserviço) usando os adapters
    registrados, compara com o template e gera um relatório de compliance.

    Ex:
    tago scan s3 --template template.yaml
    tago scan lambda functions --template template.yaml
    tago scan lambda layers --template template.yaml

    Quando --output é informado, grava o relatório em arquivo e confirma no CLI.
    """
    report = scan_resources(
        service=service,
        service_type=service_type,
        template_path=str(template),
        profile=profile,
        region=region,
    )

    report_yaml = report.to_yaml()

    if not output:
        typer.echo(report_yaml)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report_yaml, encoding="utf-8")

        typer.echo(
            f"\n"
            f"{GREY}─────────────────────────────────────────────{RESET}\n"
            f"{GREEN}{BOLD}Relatório salvo com sucesso.{RESET}\n"
            f"{CYAN}{output}{RESET}\n"
            f"{GREY}─────────────────────────────────────────────{RESET}\n"
        )
