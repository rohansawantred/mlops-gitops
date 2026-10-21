#!/usr/bin/env bash
# Local smoke: sample CSV → parquet → train → MLflow file store (no cluster operators required)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DATA_SOURCE_TYPE=local
export FRAUD_SMOKE_MODE=true
export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-file:${ROOT}/mlruns}"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "==> Ensuring venv / deps (optional if already installed)"
python3 -m pip install -q -r requirements.txt

echo "==> Converting sample CSV → parquet for Feast FileSource"
python3 - <<'PY'
import pandas as pd
from pathlib import Path
root = Path(".")
csv = root / "samples" / "transactions.csv"
pq = root / "samples" / "transactions.parquet"
df = pd.read_csv(csv, parse_dates=["event_timestamp", "created_timestamp"])
df.to_parquet(pq, index=False)
print(f"wrote {pq} rows={len(df)}")
PY

echo "==> Training + logging to MLflow"
python3 - <<'PY'
import os
from pathlib import Path
from training.features import load_local_sample
from training.train import train_fraud_model
from training.evaluate import evaluate_model, passes_promotion_gate
from training.mlflow_utils import configure_mlflow, log_and_register
import joblib

df = load_local_sample()
model, params, X_test, y_test, mappings = train_fraud_model(df, n_estimators=50)
metrics = evaluate_model(model, X_test, y_test)
print("metrics:", metrics)
configure_mlflow(experiment_name="fraud-detection")
promote = passes_promotion_gate(metrics, min_pr_auc=0.3, min_f1=0.2)
run_id = log_and_register(
    model, params, metrics, X_test,
    promote_to_staging=promote,
    cat_mappings=mappings,
)
Path("artifacts").mkdir(exist_ok=True)
joblib.dump(model, "artifacts/model.joblib")
print("run_id:", run_id, "promoted:", promote)
PY

echo "==> Feast apply (local file offline store) — best effort"
if command -v feast >/dev/null 2>&1; then
  (cd feast/feature_repo && feast apply) || echo "feast apply skipped/failed (ok for minimal smoke)"
else
  echo "feast CLI not on PATH; skipped"
fi

echo "==> Smoke OK. MLflow UI: mlflow ui --backend-store-uri ${MLFLOW_TRACKING_URI}"
