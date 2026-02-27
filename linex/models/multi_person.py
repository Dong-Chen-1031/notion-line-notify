from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SourceMultiPerson:
    """Represents a regular LINE multi-person chat, but with limited data.

    The data usually comes from events.
    """

    type: Literal["room"]

    id: str
    """ID of the source multi-person chat."""

    @staticmethod
    def from_json(data: dict[str, str]) -> "SourceMultiPerson":
        return SourceMultiPerson(
            type="room",
            id=data["roomId"],
        )
