# Ponto de entrada do CLI, mantendo apenas orquestração leve sobre o core.
import typer
import typer_di

from .commands import adapters, scan, tag, whoami
from .version import version_callback


app = typer_di.TyperDI(help="Tag AWS resources based on templates + JSON overrides.")


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the version and exit.",
        callback=version_callback,
        is_eager=True,
    )
):
    """
    Callback principal do Typer para habilitar opções globais do CLI.
    """
    pass

app.command()(tag)
app.command()(adapters)
app.command()(whoami)
app.command()(scan)

if __name__ == "__main__":
    app()
