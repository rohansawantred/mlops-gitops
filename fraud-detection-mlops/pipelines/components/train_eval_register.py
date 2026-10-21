"""Train, evaluate, and register fraud model in MLflow."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd  # noqa: E402 — path setup below for package imports


def _ensure_path() -> None:
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)


def train_eval_register(
    dataset_path: str,
    *,
    tracking_uri: str | None = None,
    experiment_name: str = "fraud-detection",
    model_name: str = "fraud-detection-model",
    min_pr_auc: float = 0.5,
    min_f1: float = 0.3,
    max_depth: int = 4,
    n_estimators: int = 100,
    learning_rate: float = 0.1,
) -> dict:
    _ensure_path()
    from training.evaluate import evaluate_model, passes_promotion_gate
    from training.mlflow_utils import configure_mlflow, log_and_register
    from training.train import train_fraud_model

    path = Path(dataset_path)
    if path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        try:
            df = pd.read_parquet(path)
        except Exception:
            df = pd.read_csv(path.with_suffix(".csv"))
    model, params, X_test, y_test, cat_mappings = train_fraud_model(
        df,
        max_depth=max_depth,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
    )
    metrics = evaluate_model(model, X_test, y_test)
    promote = passes_promotion_gate(metrics, min_pr_auc=min_pr_auc, min_f1=min_f1)

    configure_mlflow(
        tracking_uri=tracking_uri or os.getenv("MLFLOW_TRACKING_URI"),
        experiment_name=experiment_name,
    )
    run_id = log_and_register(
        model,
        params,
        metrics,
        X_test,
        registered_model_name=model_name,
        promote_to_staging=promote,
        cat_mappings=cat_mappings,
    )
    return {
        "run_id": run_id,
        "metrics": metrics,
        "promoted_to_staging": promote,
    }


if __name__ == "__main__":
    path = os.environ.get("TRAIN_DATASET_PATH", "/tmp/train.parquet")
    print(train_eval_register(path))
