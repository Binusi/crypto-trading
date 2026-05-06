"""LightGBM 3-class classifier wrapper (Sell / Hold / Buy).

Single pooled model across all assets, with `asset_id` as a categorical feature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from app.ml.features import ALL_FEATURE_COLUMNS, FEATURE_COLUMNS_NUMERIC

CATEGORICAL_FEATURES = ["asset_id"]
NUM_CLASSES = 3


@dataclass
class LightGBMModel:
    booster: lgb.Booster | None = None
    asset_id_codes: dict[str, int] = field(default_factory=dict)
    feature_columns: list[str] = field(default_factory=lambda: list(ALL_FEATURE_COLUMNS))

    @staticmethod
    def default_params() -> dict:
        return {
            "objective": "multiclass",
            "num_class": NUM_CLASSES,
            "metric": "multi_logloss",
            "num_leaves": 63,
            "learning_rate": 0.05,
            "min_data_in_leaf": 200,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
        }

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        num_boost_round: int = 400,
        early_stopping_rounds: int | None = 25,
        valid_frac: float = 0.15,
    ) -> "LightGBMModel":
        X = X[self.feature_columns]
        mask = y >= 0
        X = X.loc[mask]
        y = y.loc[mask]
        if len(X) == 0:
            raise ValueError("No labeled rows to train on.")

        # Time-based split: last `valid_frac` of (date-sorted) rows is validation.
        sorted_idx = X.index.get_level_values("date").argsort()
        split = int(len(X) * (1 - valid_frac))
        train_idx = sorted_idx[:split]
        valid_idx = sorted_idx[split:]

        train_set = lgb.Dataset(
            X.iloc[train_idx],
            label=y.iloc[train_idx],
            categorical_feature=CATEGORICAL_FEATURES,
        )
        valid_set = lgb.Dataset(
            X.iloc[valid_idx],
            label=y.iloc[valid_idx],
            categorical_feature=CATEGORICAL_FEATURES,
            reference=train_set,
        )

        callbacks = [lgb.log_evaluation(period=0)]
        if early_stopping_rounds:
            callbacks.append(lgb.early_stopping(early_stopping_rounds, verbose=False))

        self.booster = lgb.train(
            self.default_params(),
            train_set,
            num_boost_round=num_boost_round,
            valid_sets=[valid_set],
            callbacks=callbacks,
        )
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.booster is None:
            raise RuntimeError("Model not trained.")
        X = X[self.feature_columns]
        return self.booster.predict(X)

    def save(self, path: Path) -> None:
        if self.booster is None:
            raise RuntimeError("Cannot save an untrained model.")
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "booster_text": self.booster.model_to_string(),
                "asset_id_codes": self.asset_id_codes,
                "feature_columns": self.feature_columns,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> "LightGBMModel":
        blob = joblib.load(path)
        booster = lgb.Booster(model_str=blob["booster_text"])
        m = cls(
            booster=booster,
            asset_id_codes=blob["asset_id_codes"],
            feature_columns=blob.get("feature_columns", list(ALL_FEATURE_COLUMNS)),
        )
        return m


def numeric_feature_columns() -> list[str]:
    return list(FEATURE_COLUMNS_NUMERIC)
