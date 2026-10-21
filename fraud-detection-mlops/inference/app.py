"""FastAPI fraud scorer: entity ids → Feast online features → MLflow/XGBoost model."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

FEATURE_COLUMNS = ["amount", "merchant_category", "channel", "country"]

app = FastAPI(title="fraud-detection-inference", version="0.1.0")


class ScoreRequest(BaseModel):
    transaction_id: str
    customer_id: str
    # Optional overrides when Feast online is unavailable (smoke / fallback)
    features: dict[str, Any] | None = None


class ScoreResponse(BaseModel):
    transaction_id: str
    customer_id: str
    fraud_probability: float
    is_fraud_prediction: int = Field(description="1 if probability >= threshold")
    threshold: float
    feature_source: str


@lru_cache
def _load_model():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    model_uri = os.getenv(
        "MODEL_URI",
        "models:/fraud-detection-model/Staging",
    )
    mlflow.set_tracking_uri(tracking_uri)
    try:
        return mlflow.sklearn.load_model(model_uri)
    except Exception:
        local = os.getenv("LOCAL_MODEL_PATH")
        if local and Path(local).exists():
            import joblib

            return joblib.load(local)
        raise


def _encode_row(row: dict[str, Any], mappings: dict[str, dict[str, int]] | None) -> pd.DataFrame:
    data = {k: row.get(k) for k in FEATURE_COLUMNS}
    df = pd.DataFrame([data])
    if mappings:
        for col, mapping in mappings.items():
            df[col] = df[col].fillna("unknown").astype(str).map(lambda x: mapping.get(x, -1))
    else:
        # Numeric passthrough if already encoded ints
        for col in ("merchant_category", "channel", "country"):
            if df[col].dtype == object:
                df[col] = df[col].astype("category").cat.codes
    return df[FEATURE_COLUMNS]


def fetch_online_features(transaction_id: str, customer_id: str) -> tuple[dict[str, Any], str]:
    if os.getenv("FRAUD_SMOKE_MODE", "").lower() in {"1", "true"}:
        return {
            "amount": 100.0,
            "merchant_category": "grocery",
            "channel": "pos",
            "country": "US",
        }, "smoke"

    repo = os.getenv(
        "FEAST_REPO_PATH",
        str(Path(__file__).resolve().parents[1] / "feast" / "feature_repo"),
    )
    try:
        from feast import FeatureStore

        store = FeatureStore(repo_path=repo)
        resp = store.get_online_features(
            features=[
                "transaction_features:amount",
                "transaction_features:merchant_category",
                "transaction_features:channel",
                "transaction_features:country",
            ],
            entity_rows=[{"transaction_id": transaction_id, "customer_id": customer_id}],
        ).to_dict()
        row = {k: (v[0] if isinstance(v, list) else v) for k, v in resp.items()}
        return row, "feast-online"
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"Feast online unavailable: {exc}") from exc


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest):
    threshold = float(os.getenv("FRAUD_THRESHOLD", "0.5"))
    if req.features:
        feats, source = req.features, "request"
    else:
        feats, source = fetch_online_features(req.transaction_id, req.customer_id)

    model = _load_model()
    X = _encode_row(feats, mappings=None)
    try:
        proba = float(model.predict_proba(X)[:, 1][0])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model inference failed: {exc}") from exc

    return ScoreResponse(
        transaction_id=req.transaction_id,
        customer_id=req.customer_id,
        fraud_probability=proba,
        is_fraud_prediction=int(proba >= threshold),
        threshold=threshold,
        feature_source=source,
    )
