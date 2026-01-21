from importlib.metadata import PackageNotFoundError, version

import typer


def get_version() -> str:
    """
    Retorna a versão instalada do pacote, com fallback seguro se não houver metadados.
    """
    try:
        return version("tago")
    except PackageNotFoundError:
        return "unknown"


def version_callback(value: bool) -> None:
    """
    Imprime a versão e encerra a execução quando a flag --version é informada.
    """
    if value:
        print(get_version())
        raise typer.Exit()
