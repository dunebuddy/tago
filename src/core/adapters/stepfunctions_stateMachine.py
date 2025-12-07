from typing import Dict, List
from boto3.session import Session

from .base import BaseTagAdapter
from ..models import TagSet
from ..arn import Arn


class StepFunctionsStateMachineTagAdapter(BaseTagAdapter):
    service = "states"

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        """
        Suporta ARNs de Step Functions State Machines, ex:
        arn:aws:states:sa-east-1:123456789012:stateMachine:MeuStateMachine
        """
        return (
            arn.service == "states"
            and arn.resource.startswith("stateMachine:")
        )

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("stepfunctions")

    def get_context(self) -> Dict[str, str]:
        """
        Contexto específico para Step Functions.
        """
        return {
            "service_type": "workflow",
            "resource_type": "stepfunctions-state-machine",
        }

    def _to_stepfunctions_format(self, tags: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Converte [{Key, Value}] para o formato de Step Functions: [{key, value}].
        """
        return [{"key": t["Key"], "value": t["Value"]} for t in tags]

    def get_current_tags(self) -> Dict[str, str]:
        """
        Lê as tags atuais da State Machine e retorna como {key: value}.
        A API de Step Functions usa 'tags': [{'key', 'value'}].
        """
        resource_arn = self.arn.raw

        try:
            resp = self.client.list_tags_for_resource(
                resourceArn=resource_arn,
            )
            raw_tags = resp.get("tags", [])
        except Exception:
            raw_tags = []

        return {t["key"]: t["value"] for t in raw_tags}

    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> None:
        resource_arn = self.arn.raw

        # desired_tags, existing_tags, final_tags sempre em formato [{Key, Value}]
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if dry_run:
            self._print_dry_run(
                desired_tags,
                existing_tags,
                final_tags,
                "Step Functions State Machine",
                override,
            )
            return

        # Converte para o formato que a API de Step Functions espera
        sf_tags = self._to_stepfunctions_format(final_tags)

        self.client.tag_resource(
            resourceArn=resource_arn,
            tags=sf_tags,
        )
