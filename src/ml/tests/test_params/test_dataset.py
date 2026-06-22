import pytest

from common.core.entities.ml import roman_to_int
from ml.params.dataset import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    load_group_a_classic,
    to_training_frame,
)


def test_load_group_a_classic_has_twenty_rows():
    df = load_group_a_classic()
    assert len(df) == 20


def test_to_training_frame_columns_and_dtypes():
    frame = to_training_frame()
    assert list(frame.columns[: len(FEATURE_COLUMNS) + 1]) == ["patient_id", *FEATURE_COLUMNS]
    for column in TARGET_COLUMNS:
        assert column in frame.columns
    assert frame["macs_pre"].between(1, 3).all()
    assert frame["sex_male"].isin([0, 1]).all()


def test_roman_to_int_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported Roman numeral"):
        roman_to_int("XII")
