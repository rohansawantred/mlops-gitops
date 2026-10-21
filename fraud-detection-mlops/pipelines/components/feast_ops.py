"""Feast apply + materialize / historical retrieval helpers."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _default_repo() -> str:
    return os.getenv(
        "FEAST_REPO_PATH",
        str(Path(__file__).resolve().parents[2] / "feast" / "feature_repo"),
    )


def feast_apply(repo_path: str | None = None) -> str:
    repo = repo_path or _default_repo()
    subprocess.check_call(["feast", "apply"], cwd=repo)
    return f"applied:{repo}"


def feast_materialize(
    repo_path: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> str:
    from feast import FeatureStore

    repo = repo_path or _default_repo()
    store = FeatureStore(repo_path=repo)
    end_dt = (
        datetime.fromisoformat(end.replace("Z", "+00:00"))
        if end
        else datetime.now(timezone.utc)
    )
    start_dt = (
        datetime.fromisoformat(start.replace("Z", "+00:00"))
        if start
        else end_dt - timedelta(days=int(os.getenv("FEAST_MATERIALIZE_DAYS", "7")))
    )
    store.materialize(start_dt, end_dt)
    return f"materialized:{start_dt.isoformat()}->{end_dt.isoformat()}"


def build_training_dataset(
    repo_path: str | None = None,
    output_path: str = "/tmp/train.parquet",
) -> str:
    import sys

    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)

    from training.features import get_historical_training_frame

    df = get_historical_training_frame(repo_path=repo_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(out, index=False)
    except Exception:
        # Fallback when pyarrow is unavailable
        csv_path = out.with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    return str(out)
