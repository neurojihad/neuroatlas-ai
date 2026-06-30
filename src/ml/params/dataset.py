"""Group A — classic PT transfer (Sakellarides/Strecker) surgical cohort."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from common.core.entities.ml import (
    BodySide,
    GroupAClassicColumn,
    GroupAClassicFeature,
    GroupAClassicTarget,
    GroupAClassicTrainingColumn,
    Sex,
    cup_to_int,
    roman_to_int,
)

DEFAULT_CSV_PATH = Path(__file__).with_name("group_a_classic.csv")

FEATURE_COLUMNS = GroupAClassicFeature.all_features()
TARGET_COLUMNS = GroupAClassicTarget.all_targets()


def load_group_a_classic(path: Path | None = None) -> pd.DataFrame:
    """Load the raw surgical cohort CSV."""
    csv_path = path or DEFAULT_CSV_PATH
    df = pd.read_csv(csv_path)
    missing = [column.value for column in GroupAClassicColumn if column.value not in df.columns]
    if missing:
        raise ValueError(f"CSV missing expected columns: {missing}")
    return df


def to_training_frame(df: pd.DataFrame | None = None, *, path: Path | None = None) -> pd.DataFrame:
    """Return numeric feature and target columns ready for model training."""
    raw = df if df is not None else load_group_a_classic(path)
    encoded = pd.DataFrame(
        {
            GroupAClassicTrainingColumn.PatientId: raw[GroupAClassicColumn.PatientId].astype(int),
            GroupAClassicFeature.AgeYears: raw[GroupAClassicColumn.AgeYears].astype(float),
            GroupAClassicFeature.SexMale: (raw[GroupAClassicColumn.Sex].str.upper() == Sex.MALE).astype(int),
            GroupAClassicFeature.SideRight: (raw[GroupAClassicColumn.Side].str.upper() == BodySide.RIGHT).astype(int),
            GroupAClassicFeature.SurgeryYear: raw[GroupAClassicColumn.SurgeryYear].astype(int),
            GroupAClassicFeature.FollowUpMonths: raw[GroupAClassicColumn.FollowUpMonths].astype(int),
            GroupAClassicFeature.MacsPre: raw[GroupAClassicColumn.MacsPre].map(roman_to_int),
            GroupAClassicFeature.GschwindTonkin: raw[GroupAClassicColumn.GschwindTonkin].map(roman_to_int),
            GroupAClassicFeature.HousePre: raw[GroupAClassicColumn.HousePre].astype(int),
            GroupAClassicFeature.ActiveSupinationPre: raw[GroupAClassicColumn.ActiveSupinationPre].astype(float),
            GroupAClassicFeature.PassiveSupinationPre: raw[GroupAClassicColumn.PassiveSupinationPre].astype(float),
            GroupAClassicFeature.RestingPositionPre: raw[GroupAClassicColumn.RestingPositionPre].astype(float),
            GroupAClassicFeature.CupPre: raw[GroupAClassicColumn.CupPre].map(cup_to_int),
            GroupAClassicTarget.DeltaActiveSupination: raw[GroupAClassicColumn.DeltaActiveSupination].astype(float),
            GroupAClassicTarget.DeltaPassiveSupination: raw[GroupAClassicColumn.DeltaPassiveSupination].astype(float),
            GroupAClassicTarget.DeltaRestingPosition: raw[GroupAClassicColumn.DeltaRestingPosition].astype(float),
        }
    )
    return encoded
