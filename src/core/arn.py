from dataclasses import dataclass


@dataclass(frozen=True)
class Arn:
    raw: str
    partition: str
    service: str
    region: str | None
    account_id: str | None
    resource: str

    @classmethod
    def parse(cls, arn: str) -> "Arn":
        parts = arn.split(":", 5)
        if len(parts) < 6 or parts[0] != "arn":
            raise ValueError(f"Invalid ARN: {arn}")

        _, partition, service, region, account_id, resource = parts

        region = region or None
        account_id = account_id or None

        return cls(
            raw=arn,
            partition=partition,
            service=service,
            region=region,
            account_id=account_id,
            resource=resource,
        )
