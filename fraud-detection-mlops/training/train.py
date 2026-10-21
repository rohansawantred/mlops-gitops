from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_sample_weight

from .features import FEATURE_COLUMNS, LABEL_COLUMN, encode_categoricals


def train_fraud_model(
    df: pd.DataFrame,
    *,
    test_size: float = 0.25,
    random_state: int = 42,
    max_depth: int = 4,
    n_estimators: int = 100,
    learning_rate: float = 0.1,
) -> tuple[HistGradientBoostingClassifier, dict[str, Any], pd.DataFrame, pd.Series, dict]:
    """Train gradient-boosted classifier for imbalanced fraud detection (sklearn)."""

    encoded, cat_mappings = encode_categoricals(df)
    missing = [c for c in FEATURE_COLUMNS + [LABEL_COLUMN] if c not in encoded.columns]
    if missing:
        raise ValueError(f"Training frame missing columns: {missing}")

    X = encoded[FEATURE_COLUMNS]
    y = encoded[LABEL_COLUMN].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if y.nunique() > 1 else None,
    )

    sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)

    model = HistGradientBoostingClassifier(
        max_depth=max_depth,
        max_iter=n_estimators,
        learning_rate=learning_rate,
        random_state=random_state,
    )
    model.fit(X_train, y_train, sample_weight=sample_weight)

    params = {
        "model_type": "HistGradientBoostingClassifier",
        "max_depth": max_depth,
        "n_estimators": n_estimators,
        "learning_rate": learning_rate,
        "test_size": test_size,
        "random_state": random_state,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "pos_rate": float(y.mean()),
        "class_weight": "balanced",
    }
    return model, params, X_test, y_test, cat_mappings
