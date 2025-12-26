# import re

from typing import List, Dict
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet
from ..arn import Arn


class SecretsManagerSecretTagAdapter(BaseTagAdapter):
    service = "secretsmanager"

    # _SECRET_SUFFIX_RE = re.compile(r"^(?P<base>.+)-[A-Za-z0-9]{6}$")

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        # arn:aws:secretsmanager:region:account:secret:NAME-SUFFIX
        return arn.service == "secretsmanager" and arn.resource.startswith("secret:")

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("secretsmanager")

    # def _secret_name(self) -> str:
    #     # arn.resource => "secret:secret-name-xxxxx"
    #     secret_id = self.arn.resource.split("secret:", 1)[1]

    #     m = self._SECRET_SUFFIX_RE.match(secret_id)
    #     if m:
    #         return m.group("base")

    #     return secret_id


    def _to_aws_format(self, tagset: TagSet) -> List[Dict[str, str]]:
        # Secrets Manager usa o formato Key/Value igual S3 e EC2
        return [{"Key": t.key, "Value": t.value} for t in tagset.tags]

    def get_context(self) -> dict:
        return {
            "service_type": "security",
        }

    def get_current_tags(self) -> Dict[str, str]:
        """
        Lê as tags atuais do secret no Secrets Manager e retorna como {key: value}.
        """
        # secret_id = self._secret_name()

        try:
            resp = self.client.describe_secret(SecretId=self.arn.raw)
            raw_tags = resp.get("Tags", [])
        except self.client.exceptions.ResourceNotFoundException:
            raw_tags = []
        except Exception:
            # Em caso de erro inesperado, considera sem tags
            raw_tags = []

        return {t["Key"]: t["Value"] for t in raw_tags}

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> None:
        # secret_id = self._secret_name()

        # desired_tags, existing_tags, final_tags já vêm em formato AWS [{Key,Value}]
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if dry_run:
            self._print_dry_run(
                desired_tags,
                existing_tags,
                final_tags,
                "Secrets Manager Secret",
                override,
            )
            return

        # API para tagging Secrets Manager:
        self.client.tag_resource(
            SecretId=self.arn.raw,
            Tags=final_tags,
        )
