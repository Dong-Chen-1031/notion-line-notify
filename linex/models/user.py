# ruff: noqa: E501

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class BotUser:
    """Represents a LINE bot user.

    Args:
        data (dict of str: str): The data in JSON, or dictionary.
    """

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

    def from_json(self, data: dict[str, str]) -> "BotUser":
        return BotUser(
            id=data["userId"],
            basic_id=data["basicId"],
            display_name=data["displayName"],
            picture_url=data.get("pictureUrl"),
            chat_mode=data["chatMode"],  # pyright: ignore [reportArgumentType]
            mark_as_read_mode=data["markAsReadMode"],  # pyright: ignore [reportArgumentType]
        )


class User:
    """Represents a regular LINE user.

    Args:
        data (dict of str: str): The data in JSON, or dictionary.
    """

    __slots__ = (
        "_user_id",
        "_display_name",
        "_language",
        "_picture_url",
        "_status_message",
    )

    def __init__(self, data: dict[str, str]):
        self._user_id = data["userId"]
        self._display_name = data["displayName"]
        self._language = data.get("language", "en")
        self._picture_url = data.get("pictureUrl")
        self._status_message = data.get("statusMessage")

    @property
    def id(self) -> str:
        """Represents the user ID."""
        return self._user_id

    @property
    def display_name(self) -> str:
        """The user's display name."""
        return self._display_name

    name = display_name

    @property
    def language(self) -> str:
        """User's language, as a `BCP 47 <https://www.rfc-editor.org/info/bcp47>`_ language tag.

        If the user hasn't yet consented to the LINE Privacy Policy, returns ``en``.
        e.g. ``en`` for English.
        """
        return self._language

    @property
    def picture_url(self) -> Optional[str]:
        """The user's picture URL, or avatar.

        May be none.
        """
        return self._picture_url

    avatar = picture = avatar_url = picture_url

    @property
    def status_message(self) -> Optional[str]:
        """The user's status message.

        May be none.
        """
        return self._status_message

    status = status_message

    def __repr__(self) -> str:
        return (
            f"<User id={self.id!r} display_name={self.display_name!r} "
            f"picture_url={self.picture_url!r} "
            f"language={self.language!r} status={self.status!r}>"
        )
