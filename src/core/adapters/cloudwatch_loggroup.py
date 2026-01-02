from typing import Iterable, List, Dict
from botocore.exceptions import ClientError
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet, TagRunResult
from ..arn import Arn


class CloudWatchLogGroupTagAdapter(BaseTagAdapter):
    service = "logs"
    resource_type = "log-group"
    pretty_name = "CloudWatch Log Group"

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("logs")

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        """
        Suporta ARNs de CloudWatch Logs Log Group, ex.:

        arn:aws:logs:sa-east-1:123456789012:log-group:/eks/cluster/app:*
        arn:aws:logs:sa-east-1:123456789012:log-group:/aws/lambda/meu-lambda
        """
        return arn.service == "logs" and arn.resource.startswith("log-group:")

    @classmethod
    def list_resources(cls, session: Session) -> Iterable[Arn]:
        """
        Lista todos os log groups da conta/região atual e devolve como Arn.
        """
        client = session.client("logs")
        paginator = client.get_paginator("describe_log_groups")

        for page in paginator.paginate():
            for lg in page.get("logGroups", []):
                # lg["arn"] geralmente já vem com o formato completo, ex.:
                # arn:aws:logs:sa-east-1:123456789012:log-group:/eks/...:*
                arn_str = lg.get("arn")
                if arn_str:
                    yield Arn.parse(arn_str)

    def _parse_log_group_name(self) -> str:
        """
        arn.resource => "log-group:/eks/mdb-k8s-hml-ia/open-webui:*"
        Precisamos extrair apenas o logGroupName (/eks/.../open-webui), sem o ':*'.
        """
        # Remove o prefixo "log-group:"
        resource = self.arn.resource.split("log-group:", 1)[1]
        # Se tiver sufixo ':*' (ou qualquer coisa após o primeiro ':'), cortamos
        log_group_name = resource.split(":", 1)[0]
        return log_group_name

    def _to_aws_format(self, tagset: TagSet) -> Dict[str, str]:
        """
        CloudWatch Logs usa dict[str, str] para tags.
        """
        return {t.key: t.value for t in tagset.tags}

    def get_current_tags(self) -> Dict[str, str]:
        """
        Retorna as tags atuais do log group em formato dict[str, str].
        Se o log group não tiver tags, devolve {}.
        """
        log_group_name = self._parse_log_group_name()

        try:
            resp = self.client.list_tags_log_group(logGroupName=log_group_name)
            # A API já devolve {"tags": {"Key": "Value", ...}}
            tags = resp.get("tags", {}) or {}
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            # hoje não tem um erro específico tipo "NoSuchTagSet" para logs,
            # mas mantemos um padrão similar ao do S3: se for "ResourceNotFoundException" ou afins,
            # você pode escolher o que fazer. Aqui vou tratar genericamente.
            if code in ("ResourceNotFoundException",):
                return {}
            raise

        return dict(tags)

    def get_context(self) -> Dict[str, str]:
        return {"service_type": "logging"}

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> TagRunResult:
        log_group_name = self._parse_log_group_name()

        # Mantém o mesmo contrato do S3:
        # desired_tags / existing_tags / final_tags em formato AWS:
        #   List[{"Key": str, "Value": str}]
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if not dry_run:
            # Para CloudWatch Logs, tag_log_group espera:
            #   tags = { "Key": "Value", ... }
            # então convertemos a lista AWS para dict
            tags_dict = {t["Key"]: t["Value"] for t in (final_tags or [])}

            if tags_dict:
                self.client.tag_log_group(
                    logGroupName=log_group_name,
                    tags=tags_dict,
                )

        return TagRunResult(
            arn=self.arn,
            desired_tags=desired_tags,
            existing_tags=existing_tags,
            final_tags=final_tags,
            pretty_name=self.pretty_name,
        )
