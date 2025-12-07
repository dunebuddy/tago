from typing import Dict, List, Iterable
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet
from ..arn import Arn


class LambdaFunctionTagAdapter(BaseTagAdapter):
    service = "lambda"
    resource_type = "functions"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        """
        Suporta ARNs de Lambda Function, ex:
        arn:aws:lambda:sa-east-1:123456789012:function:minha-func
        arn:aws:lambda:sa-east-1:123456789012:function:minha-func:alias
        """
        return arn.service == "lambda" and arn.resource.startswith("function:")

    @classmethod
    def list_resources(cls, session: Session) -> Iterable[Arn]:
        client = session.client("lambda")
        paginator = client.get_paginator("list_functions")
        for page in paginator.paginate():
            for fn in page.get("Functions", []):
                yield Arn(fn["FunctionArn"])

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("lambda")

    def get_context(self) -> Dict[str, str]:
        return {
            "service_type": "compute",
        }

    def _to_lambda_format(self, tags: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Converte lista AWS [{Key,Value}] para o dict exigido pela API do Lambda.
        """
        return {t["Key"]: t["Value"] for t in tags}

    def get_current_tags(self) -> Dict[str, str]:
        """
        Lambda retorna tags como dict {"key": "value"}.
        Convertido para {key: value} igual ao padrão dos outros adapters.
        """
        resource_arn = self.arn.raw

        try:
            resp = self.client.list_tags(Resource=resource_arn)
            raw_tags = resp.get("Tags", {})
        except Exception:
            raw_tags = {}

        # Já está no formato {k: v}
        return raw_tags

    def apply_tags(self, tagset: TagSet, dry_run: bool = False, override: bool = False) -> None:
        resource_arn = self.arn.raw

        # desired_tags, existing_tags, final_tags → sempre [{Key,Value}]
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if dry_run:
            self._print_dry_run(
                desired_tags,
                existing_tags,
                final_tags,
                "Lambda Function",
                override
            )
            return

        # Converte final_tags para o formato do Lambda ({key: value})
        lambda_format = self._to_lambda_format(final_tags)

        self.client.tag_resource(
            Resource=resource_arn,
            Tags=lambda_format,
        )
