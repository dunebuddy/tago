import boto3
import sys
from botocore.exceptions import BotoCoreError, ClientError
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, TypeVar


from ..models import AwsIdentity, AwsIdentityError

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

        try:
            _ = get_current_aws_identity(profile=profile, region=region)
        except AwsIdentityError as exc:
            raise(exc)

        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]