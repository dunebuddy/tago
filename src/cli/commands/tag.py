import json
from pathlib import Path
from typing import Optional, List

import typer
import typer_di
import yaml

from core.engine.identity_engine import requires_aws_identity
from core.engine.tag_engine import tag_resources
from core.models import TagRunResult

from ..params import output_params

from .console import BOLD, CYAN, GREEN, GREY, MAGENTA, RED, RESET, YELLOW, BLUE

def _load_json_str(json_str: Optional[str]) -> dict:
    """
    Carrega overrides a partir de JSON inline e/ou arquivo JSON, mesclando em um dict.
    """
    data = {}
    if json_str is not None:
        data_inline = json.loads(json_str)
        data.update(data_inline)
    return data


@requires_aws_identity
# TODO: Tirar a lógica de impressão do resultado quando é dry-run da base e trazer para
# cá.
def tag(
    arns: List[str] = typer.Option(
        None,
        "--arn",
        help="ARN(s) of the resources to tag. Can be passed multiple times.",
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
    force: bool = typer.Option(
        False,
        "--force",
        help="Ignora as tags atuais e aplica só as do template + JSON.",
    ),
    output: str = typer_di.Depends(output_params),
    dev: bool = typer.Option(False, "--dev", help="Alias para --env dev"),
    hml: bool = typer.Option(False, "--hml", help="Alias para --env hml"),
    prd: bool = typer.Option(False, "--prd", help="Alias para --env prd"),
) -> None:
    """
    Aplica tags em recursos AWS usando template + JSON de merge.

    Consolida ARNs de entrada, resolve opções de ambiente e formatação de saída,
    e delega a aplicação das tags para o core.
    """
    arns = arns or []

    if not arns:
        raise typer.BadParameter(
            "Você precisa passar pelo menos um --arn ou um --arn-file."
        )

    overrides = _load_json_str(json_str)

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
        _print_tag_run(tags, force, output)
    else:
        _print_dry_run(tags, force, output)

def _print_tag_run(
    run_result: List[TagRunResult],
    override: bool,
    output: str
) -> None:
    for r in run_result:
        """
        Exibe o resultado da execução.
        """
        if output == "json":
            typer.echo(json.dumps(r.applied_tags, indent=2, ensure_ascii=False))
            return
        elif output == "yaml":
            typer.echo(yaml.dump(r.applied_tags, allow_unicode=True))
            return

        applied_tags = r.applied_tags or {}
        final_sorted = sorted(applied_tags.items(), key=lambda item: item[0].lower())
        max_key_len = max((len(key) for key, _ in final_sorted), default=0)
        
        # Cabeçalho
        print()
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print(f"{CYAN}{BOLD}RESOURCE:{RESET} {r.arn}")
        print(f"{CYAN}{BOLD}TYPE:   {RESET} {r.pretty_name}")
        mode_label = "OVERRIDE (desired overwrites existing)" if override else "SAFE (preserve existing on conflicts)"
        print(f"{YELLOW}{BOLD}MODE:   TAG RUN — {mode_label}{RESET}")
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print()

        # Desired
        print(f"{CYAN}{BOLD}Applied Tags (from template/context):{RESET}")
        if final_sorted:
            for key, value in final_sorted:
                print(f"  {key:<{max_key_len}} = {value}")
        else:
            print(GREY + "  (none)" + RESET)
        print()
    

def _print_dry_run(
    run_result: List[TagRunResult],
    override: bool,
    output: str
) -> None:
    """
    Mostra um diff cinematográfico entre:
    - desired_tags: tags geradas pelo Tago (template + contexto)
    - existing_tags: tags atualmente no recurso
    - final_tags: tags que ficariam após aplicar (levando em conta override)

    override = False  -> modo seguro: valor EXISTENTE ganha em conflitos
    override = True   -> modo agressivo: valor DESEJADO ganha em conflitos
    """

    for r in run_result:
        desired_tags = r.desired_tags
        existing_tags = r.existing_tags
        final_tags = r.final_tags

        # Ordenação consistente
        desired_sorted = sorted(desired_tags.items(), key=lambda item: item[0].lower())
        existing_sorted = sorted(existing_tags.items(), key=lambda item: item[0].lower())
        final_sorted = sorted(final_tags.items(), key=lambda item: item[0].lower())

        if output == "json":
            typer.echo(
                json.dumps(
                    {"desired": desired_tags, "existing": existing_tags, "final": final_tags},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        elif output == "yaml":
            typer.echo(
                yaml.dump(
                    {"desired": desired_tags, "existing": existing_tags, "final": final_tags},
                    allow_unicode=True,
                )
            )
            return

        desired_map = desired_tags
        existing_map = existing_tags
        final_map = final_tags

        # Padding baseado em TODAS as chaves
        all_keys = list(desired_map.keys()) + list(existing_map.keys()) + list(final_map.keys())
        max_key_len = max((len(key) for key in all_keys), default=0)

        # Conjuntos
        desired_keys = set(desired_map.keys())
        existing_keys = set(existing_map.keys())
        final_keys = set(final_map.keys())

        # Categorias principais
        added_keys = final_keys - existing_keys                 # não existia antes, agora passa a existir
        preserved_legacy_keys = existing_keys - desired_keys    # não está no template, mas já existia e foi mantida

        intersect_keys = desired_keys & existing_keys           # existe nos dois universos

        # Conflito de valor entre desired x existing
        changed_keys = {
            k for k in intersect_keys
            if desired_map.get(k) != existing_map.get(k)
        }
        unchanged_keys = intersect_keys - changed_keys

        # Cabeçalho
        print()
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print(f"{CYAN}{BOLD}RESOURCE:{RESET} {r.arn}")
        print(f"{CYAN}{BOLD}TYPE:   {RESET} {r.pretty_name}")
        mode_label = "OVERRIDE (desired overwrites existing)" if override else "SAFE (preserve existing on conflicts)"
        print(f"{YELLOW}{BOLD}MODE:   DRY RUN — {mode_label}{RESET}")
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print()

        # Desired
        print(f"{CYAN}{BOLD}Desired Tags (from template/context):{RESET}")
        if desired_sorted:
            for key, value in desired_sorted:
                print(f"  {key:<{max_key_len}} = {value}")
        else:
            print(GREY + "  (none)" + RESET)
        print()

        # Existing
        print(f"{CYAN}{BOLD}Existing Tags (currently on resource):{RESET}")
        if existing_sorted:
            for key, value in existing_sorted:
                print(f"  {key:<{max_key_len}} = {value}")
        else:
            print(GREY + "  (none)" + RESET)
        print()

        # Proposed
        print(f"{CYAN}{BOLD}Proposed Tags (final state if applied):{RESET}")
        if final_sorted:
            for key, val in final_sorted:

                if key in added_keys:
                    # tag nova
                    status = f"{GREEN}[+]{RESET}"
                elif key in preserved_legacy_keys:
                    # não está no template, mas existia e foi mantida
                    status = f"{BLUE}[•]{RESET}"
                elif key in unchanged_keys:
                    # mesmo valor em desired e existing
                    status = f"{GREEN}[=]{RESET}"
                elif key in changed_keys:
                    # conflito de valor entre desired x existing
                    if override:
                        # override ON: Tago vai SOBREESCREVER valor existente
                        status = f"{MAGENTA}[!]{RESET}"
                    else:
                        # override OFF: Tago MANTÉM valor existente
                        status = f"{YELLOW}[!]{RESET}"
                else:
                    # fallback improvável
                    status = "[ ]"

                print(f"  {status} {key:<{max_key_len}} = {val}")
        else:
            print(GREY + "  (no tags)" + RESET)

        print()
        print(GREY + "Legend:" + RESET)
        print(f"  {GREEN}[+]{RESET} added by Tago (was not present before)")
        print(f"  {GREEN}[=]{RESET} matches desired value (template/context)")
        if override:
            print(f"  {MAGENTA}[!]{RESET} existing value differs and WILL BE OVERWRITTEN (override mode)")
        else:
            print(f"  {YELLOW}[!]{RESET} existing value differs; keeping EXISTING value (safe mode)")
        print(f"  {BLUE}[•]{RESET} legacy tag (not in template), preserved as-is")
        print()
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print(f"{MAGENTA}{BOLD}DRY RUN ONLY — no changes were applied.{RESET}")
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print()
