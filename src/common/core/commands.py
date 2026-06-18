import abc
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CommandResult(Generic[T]):
    """Outcome of a command execution."""

    data: T
    first_call: bool = True


class Command(abc.ABC):
    """Base write-operation following the paymentgate command pattern.

    A command owns a frozen `Context` (validated input) plus a unit of work, and
    exposes a single `execute()` entrypoint. Read operations live in `queries.py`.
    """

    @dataclass(frozen=True)
    class Context:
        """Validated input for the command. Subclasses add their own fields."""

        def validate_context(self) -> None:
            """Hook for field validation; raise ContextValidationError on failure."""

    def __init__(self, uow, ctx: "Command.Context") -> None:
        ctx.validate_context()
        self.uow = uow
        self.ctx = ctx

    @abc.abstractmethod
    async def execute(self) -> CommandResult:
        """Run the command and return its result."""
        raise NotImplementedError
