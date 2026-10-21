# Fraud detection — source data contracts

Production data is **already available** to Feast via **S3** or **PostgreSQL**.  
Pipelines must not download external datasets as the primary path.

Set Helm `dataSource.type` to `s3` or `sql` (exactly one active).

## Common columns

| Column | Type | Required | Notes |
|---|---|---|---|
| `transaction_id` | string | yes | Entity key |
| `customer_id` | string | yes | Entity key / join |
| `event_timestamp` | timestamp (UTC) | yes | Feast event time |
| `created_timestamp` | timestamp (UTC) | recommended | Feast created time |
| `amount` | float64 | yes | Transaction amount |
| `merchant_category` | string / int | yes | MCC or category code |
| `channel` | string | optional | `pos`, `web`, `app` |
| `country` | string | optional | ISO country |
| `is_fraud` | int (0/1) | training only | Label; not used as online feature |

## S3 layout (`dataSource.type: s3`)

```text
s3://<bucket>/<prefix>/
  transactions/
    year=YYYY/month=MM/day=DD/*.parquet   # or flat *.parquet
  labels/                                 # optional separate path
    year=YYYY/month=MM/day=DD/*.parquet
```

Minimum Parquet schema for `transactions/`:

- `transaction_id`, `customer_id`, `event_timestamp`, `amount`, `merchant_category`
- Optional: `channel`, `country`, `created_timestamp`, `is_fraud`

Helm values:

```yaml
dataSource:
  type: s3
  s3:
    bucket: fraud-raw
    prefix: transactions
    endpoint: ""          # empty = AWS; set for MinIO/ODF
    region: us-east-1
    secretName: feast-s3-credentials
```

Secret keys (placeholders): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_ENDPOINT_URL`.

## SQL layout (`dataSource.type: sql`)

Default dialect: **PostgreSQL**.

```sql
CREATE TABLE fraud.transactions (
  transaction_id      TEXT PRIMARY KEY,
  customer_id         TEXT NOT NULL,
  event_timestamp     TIMESTAMPTZ NOT NULL,
  created_timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
  amount              DOUBLE PRECISION NOT NULL,
  merchant_category   TEXT NOT NULL,
  channel             TEXT,
  country             TEXT,
  is_fraud            SMALLINT  -- 0/1, training/backfill only
);

CREATE INDEX ON fraud.transactions (customer_id, event_timestamp);
```

Helm values:

```yaml
dataSource:
  type: sql
  sql:
    secretName: feast-jdbc-credentials
    schema: fraud
    table: transactions
```

Secret keys: `JDBC_URL` or (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`).

## Feast consumption

- Offline: Feast `FileSource` (S3 parquet) or `SqlSource` (Postgres table/query).
- Training: `get_historical_features` / materialization — **not** bulk copy into the pipeline image.
- Online: Redis or Postgres online store (operator-managed); inference reads features by entity keys.
