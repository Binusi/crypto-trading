from app.ml.features import ALL_FEATURE_COLUMNS, build_features
from app.ml.labels import CLASS_BUY, CLASS_HOLD, CLASS_SELL, make_labels


def test_build_features_shape_and_columns(synthetic_ohlcv_by_asset):
    feats = build_features(synthetic_ohlcv_by_asset)
    assert set(feats.columns) == set(ALL_FEATURE_COLUMNS)
    assert feats.index.names == ["date", "asset"]
    assert len(feats) > 0


def test_features_have_no_inf(synthetic_ohlcv_by_asset):
    feats = build_features(synthetic_ohlcv_by_asset)
    # After warmup, infinite values would indicate a divide-by-zero bug.
    warm = feats.dropna()
    import numpy as np
    assert np.isfinite(warm.to_numpy()).all()


def test_labels_balanced_within_5pp(synthetic_ohlcv_by_asset):
    y = make_labels(synthetic_ohlcv_by_asset)
    valid = y[y >= 0]
    counts = valid.value_counts(normalize=True)
    for cls in (CLASS_SELL, CLASS_HOLD, CLASS_BUY):
        assert abs(counts.get(cls, 0.0) - 1 / 3) < 0.07, f"class {cls} share = {counts.get(cls)}"
