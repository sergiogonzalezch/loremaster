"""Cliente S3 compatible con Floci, MinIO, Cloudflare R2 y AWS S3."""

import boto3
from botocore.config import Config

from app.core.config import settings


def get_s3_client():
    """Construye un cliente boto3 S3 apuntando al endpoint configurado."""
    kwargs: dict = {
        "region_name": settings.s3_region,
        "config": Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # path-style requerido para Floci/MinIO
            connect_timeout=5,
            read_timeout=10,
            retries={"max_attempts": 1},
        ),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)
