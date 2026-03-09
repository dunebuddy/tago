from typing import Dict, List, Optional
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet, TagRunResult
from ..arn import Arn


class APIGatewayTagAdapter(BaseTagAdapter):
    """
    Adapter para aplicar tags em API Gateway (REST API / HTTP API / WebSocket API).

    Exemplos de ARN suportados (formas comuns):
      - REST API:
        arn:aws:apigateway:sa-east-1::/restapis/a1b2c3d4e5
        arn:aws:apigateway:sa-east-1::/restapis/a1b2c3d4e5/stages/prod

      - HTTP/WebSocket (API Gateway v2):
        arn:aws:apigateway:sa-east-1::/apis/a1b2c3d4e5
        arn:aws:apigateway:sa-east-1::/apis/a1b2c3d4e5/stages/prod
    """

    service = "apigateway"
    pretty_name = "API Gateway"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        # arn:aws:apigateway:region::/restapis/...  (REST)
        # arn:aws:apigateway:region::/apis/...      (v2: HTTP/WebSocket)
        return arn.service == "apigateway" and (
            arn.resource.startswith("/restapis/") or arn.resource.startswith("/apis/")
        )

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)

        self._is_v2 = self.arn.resource.startswith("/apis/")
        self.client = self.session.client("apigatewayv2" if self._is_v2 else "apigateway")

    def get_context(self) -> Dict[str, str]:
        resource_type = "apigateway-rest" if not self._is_v2 else "apigateway-v2"
        return {
            "service_type": "network",
            "resource_type": resource_type,
        }

    def _tags_list_to_map(self, tags: List[Dict[str, str]]) -> Dict[str, str]:
        # tags em formato AWS [{Key, Value}] -> {k: v}
        return {t["Key"]: t["Value"] for t in tags}

    def _map_to_tag_payload(self, tags: List[Dict[str, str]]) -> Dict[str, str]:
        # API Gateway espera dict {k: v}
        return self._tags_list_to_map(tags)

    def get_current_tags(self) -> Dict[str, str]:
        resource_arn = self.arn.raw

        try:
            if self._is_v2:
                resp = self.client.get_tags(ResourceArn=resource_arn)
                return resp.get("Tags", {}) or {}
            else:
                resp = self.client.get_tags(resourceArn=resource_arn)
                return resp.get("tags", {}) or {}
        except Exception:
            return {}

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> TagRunResult:
        resource_arn = self.arn.raw

        # Sempre em formato [{Key, Value}]
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        desired_map = self._aws_tags_to_dict(desired_tags)
        existing_map = self._aws_tags_to_dict(existing_tags)
        final_map = self._aws_tags_to_dict(final_tags)

        if not dry_run:
            # 1) aplica/atualiza
            payload = self._map_to_tag_payload(final_tags)

            if self._is_v2:
                self.client.tag_resource(ResourceArn=resource_arn, Tags=payload)
            else:
                self.client.tag_resource(resourceArn=resource_arn, tags=payload)

            # 2) se override=True, remove tags que não devem mais existir
            if override:
                keys_to_remove = sorted(set(existing_map.keys()) - set(final_map.keys()))
                if keys_to_remove:
                    if self._is_v2:
                        self.client.untag_resource(ResourceArn=resource_arn, TagKeys=keys_to_remove)
                    else:
                        self.client.untag_resource(resourceArn=resource_arn, tagKeys=keys_to_remove)

        return TagRunResult(
            arn=self.arn.raw,
            desired_tags=desired_map,
            existing_tags=existing_map,
            final_tags=final_map,
            pretty_name=self.pretty_name,
        )
