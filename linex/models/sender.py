from dataclasses import dataclass


@dataclass(frozen=True)
class Sender:
    """Represents a sender.

    Args:
        name (str): Sender name. Max character limit: 20.
            Certain words such as ``LINE`` may not be used.
        icon_url (str, optional): URL of the image to display as an icon when sending
            a message
    """

    name: str | None
    icon_url: str | None

    def __post_init__(self):
        if not self.name and not self.icon_url:
            raise ValueError("Must provide either the name or the icon URL, or both.")

        if self.name and "line" in self.name.lower():
            raise ValueError(
                "The word 'LINE' shouldn't be in a name, it'd get rejected."
            )

    def to_json(self):
        """Converts to a valid JSON payload."""
        return {"name": self.name, "iconUrl": self.icon_url}
