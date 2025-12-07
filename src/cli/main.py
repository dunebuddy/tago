import json
import yaml
from pathlib import Path
from typing import Optional, List

import typer  # microframework de CLI = Command Line Interface

from importlib.metadata import version, PackageNotFoundError

from core.adapters import load_adapters
from core.adapters.base import BaseTagAdapter
from core.aws_identity import requires_aws_identity
from core.tag_engine import tag_resources
from core.scan_engine import scan_resources


app = typer.Typer(help="Tag AWS resources based on templates + JSON overrides.")

def get_version():
    try:
        return version("tago")
    except PackageNotFoundError:
        return "unknown"

def version_callback(value: bool):
    if value:
        print(get_version())
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the version and exit.",
        callback=version_callback,
        is_eager=True,
    )
):
    pass


def _load_json_str_or_file(json_str: Optional[str], json_file: Optional[Path]) -> dict:
    data = {}
    if json_file is not None:
        data = json.loads(json_file.read_text(encoding="utf-8"))
    if json_str is not None:
        data_inline = json.loads(json_str)
        data.update(data_inline)
    return data


@app.command()
@requires_aws_identity
def tag(
    show_identity: bool = typer.Option(False, "--show-identity", help="Mostra a identidade AWS atual junto com o output."),
    arns: List[str] = typer.Option(
        None,
        "--arn",
        help="ARN(s) of the resources to tag. Can be passed multiple times.",
    ),
    arn_file: Optional[Path] = typer.Option(
        None,
        "--arn-file",
        help="File with one ARN per line.",
    ),
    template: Path = typer.Option(
        ...,
        "--template",
        "-t",
        help="Path to template YAML/JSON file.",
    ),
    json_str: Optional[str] = typer.Option(
        None,
        "--overrides",
        help="Inline JSON overrides.",
    ),
    json_file: Optional[Path] = typer.Option(
        None,
        "--overrides-file",
        help="Path to JSON file with overrides.",
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
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not call AWS; just print what would be done.",
    ),
    env: Optional[str] = typer.Option(
        None,
        "--env",
        help="Environment (dev|hml|prd).",
    ),
    dev: bool = typer.Option(False, "--dev", help="Alias para --env dev"),
    hml: bool = typer.Option(False, "--hml", help="Alias para --env hml"),
    prd: bool = typer.Option(False, "--prd", help="Alias para --env prd"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Ignora as tags atuais e aplica só as do template + JSON.",
    ),
    output: str = typer.Option(
        "json",
        "--output",
        help="Output format: json (default) ou yaml.",
    ),
    out_json: bool = typer.Option(False, "--json", help="Alias para --output json"),
    out_yaml: bool = typer.Option(False, "--yaml", help="Alias para --output yaml"),
):
    """
    Aplica tags em recursos AWS usando template + JSON de merge.
    """
    arns: List[str] = arns or []
    if arn_file:
        extra = [
            line.strip()
            for line in arn_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        arns.extend(extra)

    if not arns:
        raise typer.BadParameter(
            "Você precisa passar pelo menos um --arn ou um --arn-file."
        )

    overrides = _load_json_str_or_file(json_str, json_file)

    # A parte de configuração de ambiente pelas opções de CLI é a parte com
    # menor precedência, ou seja, só é aplicada se a tag não vier em qualquer
    # outro lugar (template ou JSON de overrides).
    if sum([dev, hml, prd, bool(env)]) > 1:
        raise typer.BadParameter(
            "Use apenas uma opção de ambiente: --env, --dev, --hml ou --prd."
        )

    if dev:
        env = "dev"
    elif hml:
        env = "hml"
    elif prd:
        env = "prd"

    if env:
        overrides.setdefault("environment", env)

    if out_json:
        output = "json"
    elif out_yaml:
        output = "yaml"

    tags = tag_resources(
        arns=arns,
        template_path=str(template),
        overrides=overrides,
        profile=profile,
        region=region,
        dry_run=dry_run,
        override=force,
    )

    if not dry_run:
        if output not in ("json", "yaml"):
            output = "json"

        if output == "json":
            typer.echo(json.dumps(tags, indent=2, ensure_ascii=False))
        elif output == "yaml":
            typer.echo(yaml.dump(tags, allow_unicode=True))


@app.command()
def adapters() -> None:
    """
    Lista todos os adapters registrados no Tago.
    """
    # Garante que todos os módulos de adapters foram importados
    load_adapters()

    CYAN = "\033[36m"
    GREEN = "\033[32m"
    GREY = "\033[90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    print()
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print(f"{CYAN}{BOLD}Registered Adapters:{RESET}")
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print()

    if not BaseTagAdapter.registry:
        print("  (none registered)")
        print()
        return

    # ordena pela classe pra ficar estável
    for adapter in sorted(BaseTagAdapter.registry, key=lambda c: c.__name__.lower()):
        name = adapter.__name__
        service = getattr(adapter, "service", None)

        if service:
            print(f"  {GREEN}•{RESET} {name:<40} {GREY}(service={service}){RESET}")
        else:
            print(f"  {GREEN}•{RESET} {name}")

    print()
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print()


@app.command()
@requires_aws_identity
def whoami(
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
    Mostra a identidade AWS atual (Account ID, User ARN).
    """
    pass


@app.command("scan")
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
):
    """
    Varre recursos de um serviço (e opcionalmente subserviço) usando os adapters
    registrados, compara com o template e gera um relatório de compliance.

    Ex:
    tago scan s3 --template template.yaml
    tago scan lambda functions --template template.yaml
    tago scan lambda layers --template template.yaml
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

        RESET   = "\033[0m"
        BOLD    = "\033[1m"
        CYAN    = "\033[36m"
        GREEN   = "\033[32m"
        GREY    = "\033[90m"

        typer.echo(
            f"\n"
            f"{GREY}─────────────────────────────────────────────{RESET}\n"
            f"{GREEN}{BOLD}Relatório salvo com sucesso.{RESET}\n"
            f"{CYAN}{output}{RESET}\n"
            f"{GREY}─────────────────────────────────────────────{RESET}\n"
        )

if __name__ == "__main__":
    app()
