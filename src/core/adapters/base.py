from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Iterable, List, Type
from boto3.session import Session
from ..arn import Arn
from ..models import TagSet, TagRunResult


class BaseTagAdapter(ABC):
    """
    Classe base para todos os adapters.

    Ela mantém um registry automático de subclasses concretas,
    e cada subclass precisa implementar `supports(arn)`.
    """

    # registro global de adapters concretos
    registry: ClassVar[List[Type["BaseTagAdapter"]]] = []

    # Serviço AWS correspondente (lambda, s3, states...)
    service: str = ""

    # Tipo de recurso dentro do serviço (functions, layers, buckets...)
    resource_type: str | None = None
    # Nome amigavel para exibição em CLI
    pretty_name: str = ""

    def __init_subclass__(cls, **kwargs):
        """
        Sempre que uma subclass é criada, se não for abstrata, entra no registry.
        """
        super().__init_subclass__(**kwargs)

        # Se tiver métodos abstratos ainda, não registra
        if getattr(cls, "__abstractmethods__", None):
            return

        BaseTagAdapter.registry.append(cls)

    def __init__(self, arn: Arn, session: Session) -> None:
        self.arn = arn
        self.session = session

    @classmethod
    @abstractmethod
    def supports(cls, arn: Arn) -> bool:
        """
        Retorna True se esse adapter sabe lidar com o ARN informado.
        Ex: service == 's3', resource começa com 'instance/', etc.
        """
        ...
    
    @classmethod
    def list_resources(cls, session: Session) -> Iterable[Arn]:
        raise NotImplementedError("Adapter does not implement resource listing.")

    @abstractmethod
    def get_current_tags(self) -> Dict[str, str]:
        """
        Retorna as tags atuais do recurso como dict {Key: Value}.
        """
        ...

    @abstractmethod
    def apply_tags(
        self,
        tagset: TagSet,
        dry_run: bool = False,
        override: bool = False,
    ) -> TagRunResult: ...

    @abstractmethod
    def get_context(self) -> dict: ...

  
    def _build_aws_tags(self, tags: Dict[str, str]) -> List[Dict[str, str]]:
        return [{"Key": k, "Value": v} for k, v in tags.items()]
    
    def _get_aws_tags(self, tagset: TagSet, override: bool) -> tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Returns:
            (desired_tags, existing_tags, final_tags), all in AWS [{Key, Value}] format.
        """

        desired_dict: Dict[str, str] = {t.key: t.value for t in tagset.tags}
        existing = self.get_current_tags()

        if not override:
            final_dict = {**desired_dict, **existing}
        else:
            final_dict = {**existing, **desired_dict}

        return (self._build_aws_tags(desired_dict), self._build_aws_tags(existing), self._build_aws_tags(final_dict))
