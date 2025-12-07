import boto3
import sys
from botocore.exceptions import BotoCoreError, ClientError
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, TypeVar


from .models import AwsIdentity, AwsIdentityError

T = TypeVar("T", bound=Callable[..., Any])

def get_current_aws_identity(
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> AwsIdentity:
    """
    Tenta descobrir a identidade AWS atual usando STS (Security Token Service),
    respeitando profile/region passados explicitamente (se houver).
    """
    session = boto3.session.Session(
        profile_name=profile,
        region_name=region,
    )
    sts = session.client("sts")

    try:
        resp = sts.get_caller_identity()
    except (BotoCoreError, ClientError) as e:
        raise AwsIdentityError(f"Não foi possível obter a identidade AWS atual: {e}") from e

    return AwsIdentity(
        account=resp["Account"],
        arn=resp["Arn"],
        user_id=resp["UserId"],
        region=session.region_name,
        profile=session.profile_name,
    )

def requires_aws_identity(func: T) -> T:
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Typer injeta as opções como kwargs com o MESMO nome dos parâmetros
        profile = kwargs.get("profile")
        region = kwargs.get("region")
        show_identity = kwargs.get("show_identity")

        identity: Optional[AwsIdentity] = None
        error_msg: Optional[str] = None

        try:
            identity = get_current_aws_identity(profile=profile, region=region)
        except AwsIdentityError as exc:
            error_msg = str(exc)

        if show_identity:
            _print_identity(identity, error_msg)
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def _print_identity(identity: Optional[AwsIdentity], error: Optional[str]) -> None:
    import sys

    # ANSI colors
    RESET   = "\033[0m"
    BOLD    = "\033[1m"

    CYAN    = "\033[36m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    MAGENTA = "\033[35m"
    RED     = "\033[31m"
    GREY    = "\033[90m"

    if error:
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
        sys.exit(1)

    # Sucesso: identidade nunca deveria ser None aqui
    assert identity is not None

    account = identity.account
    arn     = identity.arn
    profile = identity.profile or "(no profile / env creds)"
    region  = identity.region or "(no default region)"

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