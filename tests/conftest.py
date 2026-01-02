import sys
from pathlib import Path


# Garante que `src/` está no PYTHONPATH quando rodar pytest no repo.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# Alguns ambientes de teste não têm `typer-di` instalado (dep do CLI).
# Para os testes de CLI, basta um stub compatível com a API usada.
try:  # pragma: no cover
    import typer_di  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import types
    import typer

    m = types.ModuleType("typer_di")

    class TyperDI(typer.Typer):
        pass

    def Depends(fn):
        # Typer aceita `Depends` como no FastAPI; aqui só devolvemos o callable
        return fn

    m.TyperDI = TyperDI
    m.Depends = Depends
    sys.modules["typer_di"] = m
