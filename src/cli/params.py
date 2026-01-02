import typer


def output_params(
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json (default) ou yaml.",
    ),
    out_json: bool = typer.Option(False, "--json", help="Alias para --output json"),
    out_yaml: bool = typer.Option(False, "--yaml", help="Alias para --output yaml"),
    out_text: bool = typer.Option(False, "--text", help="Alias para --output text"),
) -> str:
    output_options = [
        out_json,
        out_yaml,
        out_text,
        output is not None,  # só conta se o usuário forneceu --output
    ]

    if sum(output_options) > 1:
        raise typer.BadParameter(
            "Use apenas uma opção de output: --json, --yaml, --text ou --output."
        )

    if out_json:
        output = "json"
    elif out_yaml:
        output = "yaml"
    elif out_text:
        output = "text"

    if output not in {"json", "yaml", "text"}:
        output = "json"

    return output
