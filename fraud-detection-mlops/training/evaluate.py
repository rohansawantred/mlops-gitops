from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def recall_at_precision(
    y_true: np.ndarray | pd.Series,
    y_prob: np.ndarray,
    target_precision: float = 0.8,
) -> float:
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    eligible = precision >= target_precision
    if not np.any(eligible):
        return 0.0
    return float(np.max(recall[eligible]))


def evaluate_model(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    *,
    target_precision: float = 0.8,
) -> dict[str, Any]:
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    metrics: dict[str, Any] = {
        "pr_auc": float(average_precision_score(y_test, y_prob)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)) if y_test.nunique() > 1 else 0.0,
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        f"recall_at_precision_{target_precision}": recall_at_precision(
            y_test, y_prob, target_precision
        ),
    }
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    metrics["tn"], metrics["fp"], metrics["fn"], metrics["tp"] = (
        int(cm[0, 0]),
        int(cm[0, 1]),
        int(cm[1, 0]),
        int(cm[1, 1]),
    )
    return metrics


def passes_promotion_gate(
    metrics: dict[str, Any],
    *,
    min_pr_auc: float = 0.5,
    min_f1: float = 0.3,
) -> bool:
    return metrics.get("pr_auc", 0.0) >= min_pr_auc and metrics.get("f1", 0.0) >= min_f1
