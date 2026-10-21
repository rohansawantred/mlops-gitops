"""Validate Feast can see configured S3 or SQL sources (connectivity smoke)."""

from __future__ import annotations

import os


def validate_sources() -> str:
    source_type = os.getenv("DATA_SOURCE_TYPE", "local").lower()
    if source_type == "local":
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        parquet = root / "samples" / "transactions.parquet"
        csv = root / "samples" / "transactions.csv"
        if not parquet.exists() and not csv.exists():
            raise FileNotFoundError("Local sample transactions missing")
        return f"ok:local:{parquet if parquet.exists() else csv}"

    if source_type == "s3":
        import s3fs

        bucket = os.environ["FEAST_S3_BUCKET"]
        prefix = os.getenv("FEAST_S3_PREFIX", "transactions").strip("/")
        endpoint = os.getenv("AWS_ENDPOINT_URL") or os.getenv("FEAST_S3_ENDPOINT") or None
        fs = s3fs.S3FileSystem(
            client_kwargs={"endpoint_url": endpoint} if endpoint else None,
        )
        path = f"{bucket}/{prefix}"
        listing = fs.ls(path)
        if not listing:
            raise RuntimeError(f"No objects under s3://{path}")
        return f"ok:s3:s3://{path} ({len(listing)} entries)"

    if source_type in {"sql", "jdbc"}:
        from sqlalchemy import create_engine, text

        url = os.getenv("JDBC_URL") or os.getenv("DATABASE_URL")
        if not url:
            host = os.environ["PGHOST"]
            port = os.getenv("PGPORT", "5432")
            db = os.environ["PGDATABASE"]
            user = os.environ["PGUSER"]
            password = os.environ["PGPASSWORD"]
            url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        schema = os.getenv("FEAST_SQL_SCHEMA", "fraud")
        table = os.getenv("FEAST_SQL_TABLE", "transactions")
        engine = create_engine(url)
        with engine.connect() as conn:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{table}")).scalar()
        return f"ok:sql:{schema}.{table} rows={n}"

    raise ValueError(f"Unsupported DATA_SOURCE_TYPE={source_type}")


if __name__ == "__main__":
    print(validate_sources())
