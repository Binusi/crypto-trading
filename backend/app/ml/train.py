"""CLI: fetch OHLCV for the default universe, build features+labels, train LightGBM,
walk-forward eval, and save model to settings.model_path.

Run with: `python -m app.ml.train`
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.data.binance import BinanceProvider
from app.data.universe import DEFAULT_UNIVERSE
from app.ml.features import build_features
from app.ml.labels import make_labels
from app.ml.model import LightGBMModel
from app.ml.walk_forward import walk_forward_eval

log = get_logger(__name__)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=settings.history_years)
    parser.add_argument("--end", type=str, default=None, help="ISO date; defaults to today")
    parser.add_argument("--skip-walk-forward", action="store_true")
    args = parser.parse_args()

    end = date.fromisoformat(args.end) if args.end else date.today()
    start = end - timedelta(days=args.years * 365)
    log.info("train.start", start=str(start), end=str(end), assets=len(DEFAULT_UNIVERSE))

    provider = BinanceProvider()
    ohlcv: dict = {}
    for asset in DEFAULT_UNIVERSE:
        df = provider.fetch(asset.id, start, end)
        if df.empty:
            log.warning("train.empty_data", asset=asset.id)
            continue
        ohlcv[asset.id] = df
    if "bitcoin" not in ohlcv:
        raise SystemExit("Bitcoin OHLCV missing — cannot build cross-asset features.")

    asset_id_codes = {aid: i for i, aid in enumerate(sorted(ohlcv))}

    log.info("train.build_features")
    X = build_features(ohlcv, asset_id_codes=asset_id_codes)
    y = make_labels(ohlcv)
    common = X.index.intersection(y.index)
    X = X.loc[common]
    y = y.loc[common]
    valid = (y >= 0) & X.notna().all(axis=1)
    X = X.loc[valid]
    y = y.loc[valid]
    log.info("train.dataset_shape", rows=len(X), cols=len(X.columns))

    if not args.skip_walk_forward:
        try:
            initial_end = date.fromisoformat(settings.initial_train_end)
        except ValueError:
            initial_end = end - timedelta(days=365)
        if initial_end >= end:
            initial_end = end - timedelta(days=180)
        log.info("train.walk_forward", initial_train_end=str(initial_end))
        wf = walk_forward_eval(
            X, y, asset_id_codes,
            initial_train_end=initial_end,
            block_days=settings.walk_forward_block_days,
        )
        log.info(
            "train.walk_forward.done",
            accuracy=round(wf.accuracy, 4),
            macro_f1=round(wf.report.get("macro avg", {}).get("f1-score", 0.0), 4),
        )

    log.info("train.fit_final")
    model = LightGBMModel(asset_id_codes=asset_id_codes)
    model.fit(X, y)
    settings.model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(settings.model_path)
    log.info("train.saved", path=str(settings.model_path), trained_at=datetime.utcnow().isoformat())


if __name__ == "__main__":
    main()
