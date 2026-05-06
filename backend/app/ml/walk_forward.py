"""Walk-forward expanding-window evaluation for the classifier.

Splits time into blocks: train on everything before block, predict block, slide
forward. Returns aggregate accuracy and per-class precision/recall on the
out-of-sample blocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report

from app.core.logging import get_logger
from app.ml.model import LightGBMModel

log = get_logger(__name__)


@dataclass
class WalkForwardResult:
    accuracy: float
    report: dict


def walk_forward_eval(
    X: pd.DataFrame,
    y: pd.Series,
    asset_id_codes: dict[str, int],
    initial_train_end: date,
    block_days: int = 90,
) -> WalkForwardResult:
    dates = X.index.get_level_values("date")
    overall_min = dates.min().date()
    overall_max = dates.max().date()
    if initial_train_end <= overall_min:
        raise ValueError("initial_train_end must be after the start of the data window.")

    block_start = max(initial_train_end + timedelta(days=1), overall_min)
    all_preds: list[np.ndarray] = []
    all_truth: list[np.ndarray] = []

    while block_start <= overall_max:
        block_end = min(block_start + timedelta(days=block_days - 1), overall_max)
        train_mask = (dates < pd.Timestamp(block_start)) & (y >= 0)
        block_mask = (dates >= pd.Timestamp(block_start)) & (dates <= pd.Timestamp(block_end)) & (y >= 0)

        if not train_mask.any() or not block_mask.any():
            block_start = block_end + timedelta(days=1)
            continue

        log.info(
            "walk_forward.fit",
            train_rows=int(train_mask.sum()),
            block_rows=int(block_mask.sum()),
            block_start=str(block_start),
            block_end=str(block_end),
        )
        m = LightGBMModel(asset_id_codes=asset_id_codes)
        m.fit(X.loc[train_mask], y.loc[train_mask])
        proba = m.predict_proba(X.loc[block_mask])
        preds = proba.argmax(axis=1)
        truth = y.loc[block_mask].to_numpy()

        all_preds.append(preds)
        all_truth.append(truth)
        block_start = block_end + timedelta(days=1)

    if not all_preds:
        raise RuntimeError("No walk-forward blocks produced predictions.")

    preds = np.concatenate(all_preds)
    truth = np.concatenate(all_truth)
    return WalkForwardResult(
        accuracy=float(accuracy_score(truth, preds)),
        report=classification_report(truth, preds, output_dict=True, zero_division=0),
    )
