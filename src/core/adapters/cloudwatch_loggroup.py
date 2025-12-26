from typing import Iterable, List, Dict
from botocore.exceptions import ClientError
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet
from ..arn import Arn


class CloudWatchLogGroupTagAdapter(BaseTagAdapter):
    service = "logs"
    resource_type = "log-group"

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

    def apply_tags(self, tagset: TagSet, dry_run: bool = False, override: bool = False) -> None:
        log_group_name = self._parse_log_group_name()

        # Reutiliza a mesma lógica de merge/override do S3:
        # _get_aws_tags deve devolver (desired_tags, existing_tags, final_tags)
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if dry_run:
            self._print_dry_run(
                desired_tags,
                existing_tags,
                final_tags,
                f"CloudWatch Log Group ({log_group_name})",
                override,
            )
            return

        # A API de Logs não tem "put" que substitui tudo como no S3,
        # então precisamos:
        # - se override=True: remover tags que não estão em final_tags
        # - sempre: aplicar/atualizar as de final_tags

        # existing_tags / final_tags aqui são dict[str, str]
        existing_keys = set((existing_tags or {}).keys())
        final_keys = set((final_tags or {}).keys())

        if override:
            # tags que existiam e não queremos mais:
            tags_to_remove = list(existing_keys - final_keys)
            if tags_to_remove:
                self.client.untag_log_group(
                    logGroupName=log_group_name,
                    tags=tags_to_remove,
                )

        if final_tags:
            self.client.tag_log_group(
                logGroupName=log_group_name,
                tags=final_tags,
            )
