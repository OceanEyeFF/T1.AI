from ashare_lab.trend_schema import (
    PRIMARY_TREND_HORIZONS,
    PRIMARY_TREND_LABEL_COLS,
    PRIMARY_TREND_PRED_COLS,
    infer_label_cols,
    pred_col_from_label,
    target_name_from_label,
    target_name_from_pred,
)


def test_primary_trend_schema_constants() -> None:
    assert PRIMARY_TREND_HORIZONS == (3, 5, 10)
    assert PRIMARY_TREND_LABEL_COLS == ("label_3d", "label_5d", "label_10d")
    assert PRIMARY_TREND_PRED_COLS == ("pred_3d", "pred_5d", "pred_10d")


def test_infer_label_cols_keeps_primary_trend_heads_first() -> None:
    cols = [
        "date",
        "label_1d_high",
        "label_10d",
        "label_5d",
        "label_3d",
        "label_1d_close",
        "label_1d_low",
    ]
    assert infer_label_cols(cols) == [
        "label_3d",
        "label_5d",
        "label_10d",
        "label_1d_close",
        "label_1d_high",
        "label_1d_low",
    ]


def test_label_and_prediction_name_helpers() -> None:
    assert pred_col_from_label("label_5d") == "pred_5d"
    assert pred_col_from_label("label_1d_close") == "pred_1d_close"
    assert target_name_from_label("label_10d") == "10d"
    assert target_name_from_pred("pred_3d") == "3d"
