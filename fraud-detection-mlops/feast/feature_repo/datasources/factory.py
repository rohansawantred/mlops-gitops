"""Build Feast batch source from DATA_SOURCE_TYPE env (local|s3|sql)."""

from __future__ import annotations

import os
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_transaction_source():
    from feast import FileSource
    from feast.data_format import ParquetFormat

    source_type = os.getenv("DATA_SOURCE_TYPE", "local").lower()

    if source_type == "s3":
        bucket = os.environ["FEAST_S3_BUCKET"]
        prefix = os.getenv("FEAST_S3_PREFIX", "transactions").strip("/")
        path = f"s3://{bucket}/{prefix}/"
        return FileSource(
            name="transactions_s3",
            path=path,
            file_format=ParquetFormat(),
            timestamp_field="event_timestamp",
            created_timestamp_column="created_timestamp",
        )

    if source_type in {"sql", "jdbc"}:
        try:
            from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
                PostgreSQLSource,
            )
        except ImportError:  # pragma: no cover
            from feast import SqlSource as PostgreSQLSource  # type: ignore

        schema = os.getenv("FEAST_SQL_SCHEMA", "fraud")
        table = os.getenv("FEAST_SQL_TABLE", "transactions")
        query = os.getenv(
            "FEAST_SQL_QUERY",
            f"SELECT * FROM {schema}.{table}",
        )
        return PostgreSQLSource(
            name="transactions_sql",
            query=query,
            timestamp_field="event_timestamp",
            created_timestamp_column="created_timestamp",
        )

    sample = _repo_root() / "samples" / "transactions.parquet"
    return FileSource(
        name="transactions_local",
        path=str(sample),
        file_format=ParquetFormat(),
        timestamp_field="event_timestamp",
        created_timestamp_column="created_timestamp",
    )
