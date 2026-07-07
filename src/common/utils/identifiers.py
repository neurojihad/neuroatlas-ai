import enum

from ulid import ULID

PREFIXES: dict[str, str] = {
    "patient": "pat",
    "assessment": "asm",
    "user": "usr",
    "event": "evt",
    "correlation": "crr",
}


class StringEnum:
    """Enum member helper that exposes a prefix with trailing underscore."""

    @property
    def with_delimiter(self) -> str:
        result: str = getattr(self, "value")
        return result + "_"


PrefixesEnum = enum.Enum("StringEnum", PREFIXES, type=StringEnum)  # type: ignore[misc]


def generate_id_for(id_type: str) -> str:
    """Generate a new ULID-based id with the given type prefix."""
    prefix = PREFIXES.get(id_type, "?")
    return f"{prefix}_{str(ULID()).lower()}"


def prefixed_id(id_type: str, external_id: str) -> str:
    """Build a stable id from an external identifier (e.g. Keycloak ``sub``)."""
    prefix = PREFIXES.get(id_type, "?")
    return f"{prefix}_{external_id}"
