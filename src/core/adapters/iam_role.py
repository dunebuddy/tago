from typing import Dict, List
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet, TagRunResult
from ..arn import Arn


class IAMRoleTagAdapter(BaseTagAdapter):
    service = "iam"
    pretty_name = "IAM Role"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        """
        Suporta ARNs de IAM Role, ex:
        arn:aws:iam::123456789012:role/MeuRole
        arn:aws:iam::123456789012:role/path/MeuRole
        """
        return arn.service == "iam" and arn.resource.startswith("role/")

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("iam")

    def get_context(self) -> Dict[str, str]:
        return {
            "service_type": "iam",
        }

    def _role_name(self) -> str:
        """
        Remove o prefixo `role/` para que a API do IAM aceite.
        """
        return self.arn.resource.split("role/", 1)[1]

    def get_current_tags(self) -> Dict[str, str]:
        """
        Lê as tags atuais da IAM Role e retorna como {key: value}.
        """
        role_name = self._role_name()

        try:
            resp = self.client.list_role_tags(RoleName=role_name)
            raw_tags = resp.get("Tags", [])
        except Exception:
            # IAM pode gerar erros variados — fallback seguro
            raw_tags = []

        return {t["Key"]: t["Value"] for t in raw_tags}

    def _to_aws_format(self, tagset: TagSet) -> List[Dict[str, str]]:
        """
        IAM usa lista de dicts [{Key, Value}].
        """
        return [{"Key": t.key, "Value": t.value} for t in tagset.tags]

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> TagRunResult:
        role_name = self._role_name()

        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if not dry_run:
            self.client.tag_role(
                RoleName=role_name,
                Tags=final_tags,
            )

        return TagRunResult(
            arn=self.arn,
            desired_tags=desired_tags,
            existing_tags=existing_tags,
            final_tags=final_tags,
            pretty_name=self.pretty_name,
        )
