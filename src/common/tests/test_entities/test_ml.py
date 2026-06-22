import pytest

from common.core.entities.ml import (
    GroupAClassicColumn,
    GroupAClassicFeature,
    GroupAClassicTarget,
    RomanLevel,
    cup_to_int,
    roman_to_int,
)


def test_group_a_classic_column_count():
    assert len(GroupAClassicColumn.all_columns()) == 20


def test_feature_and_target_values():
    assert GroupAClassicFeature.MacsPre == "macs_pre"
    assert GroupAClassicTarget.DeltaActiveSupination == "delta_active_supination"
    assert len(GroupAClassicFeature.all_features()) == 12
    assert len(GroupAClassicTarget.all_targets()) == 3


def test_roman_to_int_maps_enum_and_rejects_unknown():
    assert roman_to_int(RomanLevel.THREE) == 3
    assert roman_to_int("II") == 2
    with pytest.raises(ValueError, match="Unsupported Roman numeral"):
        roman_to_int("XII")


def test_cup_to_int_maps_russian_labels():
    assert cup_to_int("Нет") == 0
    assert cup_to_int("Да") == 1
