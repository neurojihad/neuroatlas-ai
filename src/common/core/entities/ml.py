"""ML domain entities: surgical cohort schemas, clinical scales, and encodings."""

import enum


class GroupAClassicColumn(enum.StrEnum):
    """Raw CSV column headers for Group A classic PT transfer (Sakellarides/Strecker).

    Member values match the source spreadsheet headers (UTF-8). Used when loading
    ``group_a_classic.csv`` and validating column presence before encoding.
    """

    PatientId = "№"
    Sex = "Пол"
    AgeYears = "Возраст_операции_лет"
    Side = "Сторона"
    SurgeryYear = "Год_операции"
    FollowUpMonths = "Срок_наблюдения_мес"
    CpForm = "Форма_ДЦП"
    MacsPre = "MACS_pre"
    GschwindTonkin = "Gschwind_Tonkin"
    HousePre = "House_pre"
    ActiveSupinationPre = "Актив_супинация_pre"
    PassiveSupinationPre = "Пассив_супинация_pre"
    RestingPositionPre = "Положение_покоя_pre"
    CupPre = "Чашка_pre"
    ActiveSupinationPost = "Актив_супинация_post"
    PassiveSupinationPost = "Пассив_супинация_post"
    RestingPositionPost = "Положение_покоя_post"
    DeltaActiveSupination = "Δ_актив_супинация"
    DeltaPassiveSupination = "Δ_пассив_супинация"
    DeltaRestingPosition = "Δ_положение_покоя"

    @classmethod
    def all_columns(cls) -> list["GroupAClassicColumn"]:
        """Return every raw CSV column enum member.

        Returns:
            List of all ``GroupAClassicColumn`` members in declaration order.
        """

        return list(cls)


class GroupAClassicFeature(enum.StrEnum):
    """Encoded ML feature column names for Group A classic cohort.

    Values are snake_case identifiers used in the numeric training frame produced
    by ``ml.params.dataset.to_training_frame()``.
    """

    AgeYears = "age_years"
    SexMale = "sex_male"
    SideRight = "side_right"
    SurgeryYear = "surgery_year"
    FollowUpMonths = "follow_up_months"
    MacsPre = "macs_pre"
    GschwindTonkin = "gschwind_tonkin"
    HousePre = "house_pre"
    ActiveSupinationPre = "active_supination_pre"
    PassiveSupinationPre = "passive_supination_pre"
    RestingPositionPre = "resting_position_pre"
    CupPre = "cup_pre"

    @classmethod
    def all_features(cls) -> tuple[str, ...]:
        """Return encoded feature column names as strings.

        Returns:
            Tuple of feature column names suitable for model input selection.
        """

        return tuple(member.value for member in cls)


class GroupAClassicTarget(enum.StrEnum):
    """Outcome targets (supination ROM deltas) for Group A classic cohort.

    Each member names a post-operative improvement column (post minus pre) used
    as a regression target during model training.
    """

    DeltaActiveSupination = "delta_active_supination"
    DeltaPassiveSupination = "delta_passive_supination"
    DeltaRestingPosition = "delta_resting_position"

    @classmethod
    def all_targets(cls) -> tuple[str, ...]:
        """Return encoded target column names as strings.

        Returns:
            Tuple of target column names suitable for model output selection.
        """

        return tuple(member.value for member in cls)


class GroupAClassicTrainingColumn(enum.StrEnum):
    """Identifier columns in the encoded training frame.

    Distinct from ``GroupAClassicFeature`` — holds non-predictive metadata retained
    for traceability (e.g. linking rows back to source patients).
    """

    PatientId = "patient_id"


class Sex(enum.StrEnum):
    """Patient sex as recorded in the surgical cohort spreadsheet."""

    MALE = "M"
    FEMALE = "F"


class BodySide(enum.StrEnum):
    """Affected body side for the PT transfer procedure."""

    RIGHT = "R"
    LEFT = "L"


class CpForm(enum.StrEnum):
    """Cerebral palsy clinical form recorded in the cohort."""

    HEMIPARESIS = "гемипарез"


class RomanLevel(enum.IntEnum):
    """Clinical scale levels encoded as Roman numerals I–V.

    Used for MACS and Gschwind-Tonkin scores in the Group A dataset. Integer
    values map to ordinal severity (1 = mildest, 5 = most severe).
    """

    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


_ROMAN_NUMERALS: dict[str, RomanLevel] = {
    "I": RomanLevel.ONE,
    "II": RomanLevel.TWO,
    "III": RomanLevel.THREE,
    "IV": RomanLevel.FOUR,
    "V": RomanLevel.FIVE,
}


class CupTestOutcome(enum.IntEnum):
    """Cup test result encoded as a binary outcome.

    The cup test assesses whether the patient can hold a cup; ``NO`` and ``YES``
    map to 0 and 1 respectively in the training frame.
    """

    NO = 0
    YES = 1


_CUP_TEST_LABELS: dict[str, CupTestOutcome] = {
    "да": CupTestOutcome.YES,
    "yes": CupTestOutcome.YES,
    "1": CupTestOutcome.YES,
    "нет": CupTestOutcome.NO,
    "no": CupTestOutcome.NO,
    "0": CupTestOutcome.NO,
}


def roman_to_int(value: str | int | RomanLevel) -> int:
    """Convert a Roman numeral or numeric string to an integer level (1–5).

    Args:
        value: Roman numeral label (``"I"``–``"V"``), digit string, plain integer,
            or ``RomanLevel`` enum member.

    Returns:
        Integer level between 1 and 5 inclusive.

    Raises:
        ValueError: If ``value`` is not a supported Roman numeral or integer string.
    """

    if isinstance(value, RomanLevel):
        return value.value
    if isinstance(value, int):
        return value
    normalized = str(value).strip().upper()
    level = _ROMAN_NUMERALS.get(normalized)
    if level is not None:
        return level.value
    if normalized.isdigit():
        return int(normalized)
    raise ValueError(f"Unsupported Roman numeral: {value!r}")


def cup_to_int(value: str | int | CupTestOutcome) -> int:
    """Convert a cup test label to a binary integer (0 = no, 1 = yes).

    Args:
        value: Russian or English label (``"Да"``/``"Нет"``, ``"yes"``/``"no"``),
            digit string, plain integer, or ``CupTestOutcome`` enum member.

    Returns:
        ``0`` for negative outcome, ``1`` for positive outcome.

    Raises:
        ValueError: If ``value`` is not a recognized cup test label.
    """

    if isinstance(value, CupTestOutcome):
        return value.value
    if isinstance(value, int):
        return value
    normalized = str(value).strip().casefold()
    outcome = _CUP_TEST_LABELS.get(normalized)
    if outcome is None:
        raise ValueError(f"Unsupported cup test value: {value!r}")
    return outcome.value
