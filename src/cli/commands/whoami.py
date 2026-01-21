import json
from dataclasses import asdict
from typing import Optional

import typer
import typer_di
import yaml

from core.engine.identity_engine import get_current_aws_identity
from core.models import AwsIdentity

from .console import BOLD, CYAN, GREEN, GREY, MAGENTA, RED, RESET, YELLOW
from ..params import output_params


def _print_identity(
    identity: Optional[AwsIdentity],
    error: Optional[Exception],
    output: Optional[str],
) -> None:
    if error:
        if output == "json":
            typer.echo(json.dumps({"error": str(error)}, indent=2, ensure_ascii=False))
            raise typer.Exit(code=1)

        if output == "yaml":
            typer.echo(yaml.safe_dump({"error": str(error)}, sort_keys=False, allow_unicode=True))
            raise typer.Exit(code=1)

        print()
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print(f"{RED}{BOLD}FAILED TO RESOLVE AWS IDENTITY{RESET}")
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print()
        print(f"{MAGENTA}Detalhes:{RESET}")
        print(f"  {error}")
        print()
        print(f"{YELLOW}Verifique se:{RESET}")
        print("  - O AWS_PROFILE está configurado corretamente")
        print("  - O login SSO está ativo (ex.: `aws sso login`)")
        print("  - As variáveis de ambiente de credenciais estão corretas")
        print("  - A role tem permissão para `sts:GetCallerIdentity`")
        print()
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print(f"{RED}{BOLD}ABORTING — nenhuma ação será executada.{RESET}")
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print()
        raise typer.Exit(code=1)

    # Sucesso: identidade nunca deveria ser None aqui
    assert identity is not None

    identity_dict = asdict(identity)

    if output == "json":
        typer.echo(json.dumps(identity_dict, indent=2, ensure_ascii=False))
        return

    if output == "yaml":
        typer.echo(yaml.safe_dump(identity_dict, sort_keys=False, allow_unicode=True))
        return

    account = identity.account
    arn = identity.arn
    profile = identity.profile or "(no profile / env creds)"
    region = identity.region or "(no default region)"

    print()
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print(f"{CYAN}{BOLD}TAGO — AWS Identity Context{RESET}")
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print(f"{CYAN}{BOLD}ACCOUNT:{RESET} {account}")
    print(f"{CYAN}{BOLD}ARN:    {RESET} {arn}")
    print(f"{CYAN}{BOLD}PROFILE:{RESET} {profile}")
    print(f"{CYAN}{BOLD}REGION: {RESET} {region}")
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print(f"{GREEN}{BOLD}Identity OK — proceeding with command execution.{RESET}")
    print(GREY + "─────────────────────────────────────────────" + RESET)
    print()


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
    output: str = typer_di.Depends(output_params),
) -> None:
    """
    Mostra a identidade AWS atual (Account ID, User ARN).

    O output é emitido pelo decorator de identidade.
    """
    identity = None
    err = None

    try:
        identity = get_current_aws_identity(profile=profile, region=region)
    except Exception as e:
        err = e

    _print_identity(identity, err, output)
