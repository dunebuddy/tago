# Tago

Tago is a CLI to standardize AWS resource tags based on templates and JSON overrides.
It helps teams keep ownership, environment, and compliance metadata consistent across
services while still allowing per-resource adjustments.

The project is intentionally simple: you provide a tag template, optionally override
values, and Tago applies (or simulates) the final tag state on supported resources.

> Disclaimer: Tago is under active development. Interfaces and behavior may change.

## Why use Tago

- Keep AWS tags consistent across services without duplicating logic
- Preview the final state before applying changes
- Use a single template with small overrides per environment/resource
- Extend through adapters to support more AWS services

## Installation

Tago can be installed as an isolated CLI using `uv tool` or `pipx`.

### Using uv tool

```bash
uv tool install tago
```

### Using pipx

```bash
pipx install tago
```

If you want to run it from source:

```bash
pip install -e .
```

## Quick start

Prepare a template (YAML):

```yaml
defaults:
  Owner: team-platform
  Environment: dev
  CostCenter: 1234
```

Apply tags to one or more resources:

```bash
tago tag \
  --arn arn:aws:s3:::my-bucket \
  --template ./template.yaml
```

Simulate changes without applying:

```bash
tago tag \
  --arn arn:aws:s3:::my-bucket \
  --template ./template.yaml \
  --dry-run
```

### JSON overrides

You can override template values inline:

```bash
tago tag \
  --arn arn:aws:lambda:us-east-1:123456789012:function:my-func \
  --template ./template.yaml \
  --overrides '{"Owner":"team-apps","Environment":"prd"}'
```

### Output formats

By default, output is JSON. You can request YAML or text:

```bash
tago tag --arn ... --template ./template.yaml --output yaml
tago tag --arn ... --template ./template.yaml --output text
```

## Commands

### `tag`

Apply tags to supported resources based on a template and overrides.

```bash
tago tag \
  --arn arn:aws:s3:::my-bucket \
  --template ./template.yaml \
  --overrides '{"Environment":"hml"}' \
  --dry-run
```

### `whoami`

Show the current AWS identity context:

```bash
tago whoami
```

### `adapters`

List all available adapters:

```bash
tago adapters
```

### `scan`

Scan resources and compare against a template (in development):

```bash
tago scan s3 --template ./template.yaml
```

## Configuration

Tago uses the standard AWS credential chain (profiles, environment variables, SSO).
You can pass `--profile` and `--region` when needed.

## Roadmap

- [x] Tagging support for multiple AWS services via adapters
- [x] Dry-run for safe preview
- [ ] Scan command (in development)

## Use of AI in Development

This project made use of Artificial Intelligence tools as support during development,
whenever appropriate, especially for:
- code review
- refactoring
- test writing
- documentation

All final decisions regarding architecture, logic, and implementation
were manually reviewed and validated.

## Contributing

Contributions are welcome. Open an issue or PR with clear context and examples.

## License

See `LICENSE`.
