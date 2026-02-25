# ruff: noqa: E501

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BotUser:
    """Represents a LINE bot user."""

    id: str
    """Represents the bot ID."""

    basic_id: str
    """Represents the bot's basic ID (@handle)."""

    display_name: str
    """The bot's display name."""

    picture_url: str | None
    """The bot's picture URL, or avatar.

    May be none.
    """

    chat_mode: Literal["chat", "bot"]
    """The chat mode.

    One of:
    * ``chat``: Chat is set to "On."
    * ``bot``: Chat is set to "Off."
    """

    mark_as_read_mode: Literal["auto", "manual"]
    """Automatic read settings for messages.

    If the "chat" feature is set to "Off", ``auto`` is returned;
    if the "chat" feature is set to "On", ``manual`` is returned.
    """

    @staticmethod
    def from_json(data: dict[str, str]) -> "BotUser":
        return BotUser(
            id=data["userId"],
            basic_id=data["basicId"],
            display_name=data["displayName"],
            picture_url=data.get("pictureUrl"),
            chat_mode=data["chatMode"],  # pyright: ignore [reportArgumentType]
            mark_as_read_mode=data["markAsReadMode"],  # pyright: ignore [reportArgumentType]
        )


@dataclass(frozen=True)
class User:
    """Represents a regular LINE user.

    Args:
        data (dict of str: str): The data in JSON, or dictionary.
    """

    id: str
    """Represents the user ID."""

    display_name: str
    """The user's display name."""

    language: str
    """User's language, as a `BCP 47 <https://www.rfc-editor.org/info/bcp47>`_ language tag.

    If the user hasn't yet consented to the LINE Privacy Policy, returns ``en``.
    e.g. ``en`` for English.
    """

    picture_url: str | None
    """The user's picture URL, or avatar.

    May be none.
    """

    status_message: str | None
    """The user's status message.

    May be none.
    """

    @staticmethod
    def from_json(data: dict[str, str]) -> "User":
        return User(
            id=data["userId"],
            display_name=data["displayName"],
            language=data.get("language", "en"),
            picture_url=data.get("pictureUrl"),
            status_message=data.get("statusMessage"),
        )
