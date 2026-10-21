from __future__ import annotations

import os
from typing import Any

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature


def configure_mlflow(
    tracking_uri: str | None = None,
    experiment_name: str = "fraud-detection",
) -> None:
    uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment_name)


def log_and_register(
    model,
    params: dict[str, Any],
    metrics: dict[str, Any],
    X_sample,
    *,
    registered_model_name: str = "fraud-detection-model",
    promote_to_staging: bool = False,
    cat_mappings: dict | None = None,
) -> str:
    """Log sklearn model to MLflow and optionally transition to Staging."""

    signature = infer_signature(X_sample, model.predict_proba(X_sample)[:, 1])
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_metrics(
            {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
        )
        if cat_mappings:
            mlflow.log_dict(cat_mappings, "categorical_mappings.json")
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            signature=signature,
            input_example=X_sample.head(3),
            registered_model_name=registered_model_name,
        )
        run_id = run.info.run_id

    if promote_to_staging:
        client = mlflow.tracking.MlflowClient()
        versions = client.get_latest_versions(registered_model_name, stages=["None"])
        if versions:
            client.transition_model_version_stage(
                name=registered_model_name,
                version=versions[0].version,
                stage="Staging",
            )
    return run_id
