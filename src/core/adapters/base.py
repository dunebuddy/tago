from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Iterable, List, Type
from boto3.session import Session
from ..arn import Arn
from ..models import TagSet


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
    def apply_tags(self, tagset: TagSet, dry_run: bool = False, override: bool = False) -> None: ...

    @abstractmethod
    def get_context(self) -> dict: ...

    def _print_dry_run(
        self,
        desired_tags: List[Dict[str, str]],
        existing_tags: List[Dict[str, str]],
        final_tags: List[Dict[str, str]],
        resource_type: str,
        override: bool,
    ) -> None:
        """
        Mostra um diff cinematográfico entre:
        - desired_tags: tags geradas pelo Tago (template + contexto)
        - existing_tags: tags atualmente no recurso
        - final_tags: tags que ficariam após aplicar (levando em conta override)

        override = False  -> modo seguro: valor EXISTENTE ganha em conflitos
        override = True   -> modo agressivo: valor DESEJADO ganha em conflitos
        """

        # ANSI colors
        RESET   = "\033[0m"
        BOLD    = "\033[1m"

        CYAN    = "\033[36m"
        GREEN   = "\033[32m"
        YELLOW  = "\033[33m"
        MAGENTA = "\033[35m"
        BLUE    = "\033[34m"
        GREY    = "\033[90m"

        # Converte listas -> dicts
        desired_map: Dict[str, str] = {t["Key"]: t["Value"] for t in desired_tags}
        existing_map: Dict[str, str] = {t["Key"]: t["Value"] for t in existing_tags}
        final_map: Dict[str, str] = {t["Key"]: t["Value"] for t in final_tags}

        # Padding baseado em TODAS as chaves
        all_tags = desired_tags + existing_tags + final_tags
        max_key_len = max((len(t["Key"]) for t in all_tags), default=0)

        # Conjuntos
        desired_keys = set(desired_map.keys())
        existing_keys = set(existing_map.keys())
        final_keys = set(final_map.keys())

        # Categorias principais
        added_keys = final_keys - existing_keys                 # não existia antes, agora passa a existir
        preserved_legacy_keys = existing_keys - desired_keys    # não está no template, mas já existia e foi mantida

        intersect_keys = desired_keys & existing_keys           # existe nos dois universos

        # Conflito de valor entre desired x existing
        changed_keys = {
            k for k in intersect_keys
            if desired_map.get(k) != existing_map.get(k)
        }
        unchanged_keys = intersect_keys - changed_keys

        # Ordenação consistente
        desired_sorted = sorted(desired_tags, key=lambda t: t["Key"].lower())
        existing_sorted = sorted(existing_tags, key=lambda t: t["Key"].lower())
        final_sorted = sorted(final_tags, key=lambda t: t["Key"].lower())

        # Cabeçalho
        print()
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print(f"{CYAN}{BOLD}RESOURCE:{RESET} {self.arn.raw}")
        print(f"{CYAN}{BOLD}TYPE:   {RESET} {resource_type}")
        mode_label = "OVERRIDE (desired overwrites existing)" if override else "SAFE (preserve existing on conflicts)"
        print(f"{YELLOW}{BOLD}MODE:   DRY RUN — {mode_label}{RESET}")
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print()

        # Desired
        print(f"{CYAN}{BOLD}Desired Tags (from template/context):{RESET}")
        if desired_sorted:
            for t in desired_sorted:
                print(f"  {t['Key']:<{max_key_len}} = {t['Value']}")
        else:
            print(GREY + "  (none)" + RESET)
        print()

        # Existing
        print(f"{CYAN}{BOLD}Existing Tags (currently on resource):{RESET}")
        if existing_sorted:
            for t in existing_sorted:
                print(f"  {t['Key']:<{max_key_len}} = {t['Value']}")
        else:
            print(GREY + "  (none)" + RESET)
        print()

        # Proposed
        print(f"{CYAN}{BOLD}Proposed Tags (final state if applied):{RESET}")
        if final_sorted:
            for t in final_sorted:
                key = t["Key"]
                val = t["Value"]

                if key in added_keys:
                    # tag nova
                    status = f"{GREEN}[+]{RESET}"
                elif key in preserved_legacy_keys:
                    # não está no template, mas existia e foi mantida
                    status = f"{BLUE}[•]{RESET}"
                elif key in unchanged_keys:
                    # mesmo valor em desired e existing
                    status = f"{GREEN}[=]{RESET}"
                elif key in changed_keys:
                    # conflito de valor entre desired x existing
                    if override:
                        # override ON: Tago vai SOBREESCREVER valor existente
                        status = f"{MAGENTA}[!]{RESET}"
                    else:
                        # override OFF: Tago MANTÉM valor existente
                        status = f"{YELLOW}[!]{RESET}"
                else:
                    # fallback improvável
                    status = "[ ]"

                print(f"  {status} {key:<{max_key_len}} = {val}")
        else:
            print(GREY + "  (no tags)" + RESET)

        print()
        print(GREY + "Legend:" + RESET)
        print(f"  {GREEN}[+]{RESET} added by Tago (was not present before)")
        print(f"  {GREEN}[=]{RESET} matches desired value (template/context)")
        if override:
            print(f"  {MAGENTA}[!]{RESET} existing value differs and WILL BE OVERWRITTEN (override mode)")
        else:
            print(f"  {YELLOW}[!]{RESET} existing value differs; keeping EXISTING value (safe mode)")
        print(f"  {BLUE}[•]{RESET} legacy tag (not in template), preserved as-is")
        print()
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print(f"{MAGENTA}{BOLD}DRY RUN ONLY — no changes were applied.{RESET}")
        print(GREY + "─────────────────────────────────────────────" + RESET)
        print()

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