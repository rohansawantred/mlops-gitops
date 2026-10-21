"""Helpers to build a training frame from Feast or local smoke parquet."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

FEATURE_COLUMNS = [
    "amount",
    "merchant_category",
    "channel",
    "country",
]
LABEL_COLUMN = "is_fraud"
ENTITY_COLUMNS = ["transaction_id", "customer_id", "event_timestamp"]


def load_local_sample(path: str | Path | None = None) -> pd.DataFrame:
    root = Path(__file__).resolve().parents[1]
    path = Path(path) if path else root / "samples" / "transactions.parquet"
    if path.exists() and path.suffix == ".parquet":
        try:
            return pd.read_parquet(path)
        except Exception:
            pass
    csv_path = root / "samples" / "transactions.csv"
    return pd.read_csv(csv_path, parse_dates=["event_timestamp", "created_timestamp"])


def encode_categoricals(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    mappings: dict = {}
    for col in ("merchant_category", "channel", "country"):
        if col not in out.columns:
            out[col] = "unknown"
        cats = sorted(out[col].fillna("unknown").astype(str).unique())
        mapping = {c: i for i, c in enumerate(cats)}
        mappings[col] = mapping
        out[col] = out[col].fillna("unknown").astype(str).map(mapping).astype(int)
    return out, mappings


def get_historical_training_frame(
    entity_df: pd.DataFrame | None = None,
    repo_path: str | None = None,
) -> pd.DataFrame:
    """Retrieve features via Feast when DATA_SOURCE_TYPE is set; else local sample."""

    source_type = os.getenv("DATA_SOURCE_TYPE", "local").lower()
    if source_type == "local" or os.getenv("FRAUD_SMOKE_MODE", "").lower() in {"1", "true"}:
        return load_local_sample()

    from feast import FeatureStore

    repo = repo_path or os.getenv(
        "FEAST_REPO_PATH",
        str(Path(__file__).resolve().parents[1] / "feast" / "feature_repo"),
    )
    store = FeatureStore(repo_path=repo)

    if entity_df is None:
        # Entity timestamps come from offline source projection (smoke-safe fallback)
        entity_df = load_local_sample()[ENTITY_COLUMNS]

    features = store.get_historical_features(
        entity_df=entity_df,
        features=[
            "transaction_features:amount",
            "transaction_features:merchant_category",
            "transaction_features:channel",
            "transaction_features:country",
            "transaction_labels:is_fraud",
        ],
    ).to_df()
    return features
