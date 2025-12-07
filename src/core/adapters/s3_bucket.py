from typing import Iterable, List, Dict
from botocore.exceptions import ClientError
from boto3.session import Session
from .base import BaseTagAdapter
from ..models import TagSet
from ..arn import Arn


class S3BucketTagAdapter(BaseTagAdapter):
    service = "s3"

    def __init__(self, arn: Arn, session: Session) -> None:
        super().__init__(arn, session)
        self.client = self.session.client("s3")

    def _parse_bucket_name(self) -> str:
        # arn:aws:s3:::bucket-name
        return self.arn.resource  # aqui geralmente já vem "bucket-name"

    def _to_aws_format(self, tagset: TagSet) -> List[Dict[str, str]]:
        return [{"Key": t.key, "Value": t.value} for t in tagset.tags]

    @classmethod
    def supports(cls, arn: Arn) -> bool:
        # arn:aws:s3:::bucket-name
        return arn.service == "s3"
    
    @classmethod
    def list_resources(cls, session: Session) -> Iterable[Arn]:
        client = session.client("s3")
        resp = client.list_buckets()
        for b in resp.get("Buckets", []):
            yield Arn.parse(b["BucketArn"])

    def get_current_tags(self) -> Dict[str, str]:
        """
        Retorna as tags atuais do bucket em formato dict[str, str].
        Se o bucket não tiver TagSet, devolve {}.
        """
        bucket_name = self._parse_bucket_name()

        try:
            response = self.client.get_bucket_tagging(Bucket=bucket_name)
            tagset = response.get("TagSet", [])
        except self.client.exceptions.NoSuchKey:
            # caminho feliz: bucket sem tags
            return {}
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "NoSuchTagSet":
                # às vezes vem embalado num ClientError
                return {}
            # outros erros (AccessDenied, etc) você escolhe:
            # - ou levanta de novo
            # - ou loga e devolve {}
            raise

        # aqui já temos TagSet no formato [{"Key": "...", "Value": "..."}, ...]
        return {t["Key"]: t["Value"] for t in tagset}

    
    def get_context(self):
        return {"service_type": "storage" }
    
    def apply_tags(self, tagset: TagSet, dry_run: bool = False, override: bool = False) -> None:
        bucket_name = self._parse_bucket_name()
        
        desired_tags, existing_tags, final_tags = self._get_aws_tags(tagset, override)

        if dry_run:
            self._print_dry_run(desired_tags, existing_tags, final_tags, "S3 Bucket", override)
            return

        self.client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={"TagSet": final_tags},
        )
