# ruff: noqa: E501

from __future__ import annotations

from typing import Literal, Optional

from .user import BotUser, User


class Mention:
    """Represents a LINE user mention.

    Args:
        type: The mention type.
        user (optional): The user object or the ID. Required when `type` is `user`.
    """

    __slots__ = ("type", "user_id")
    type: Literal["all", "user"]
    user_id: str | None

    def __init__(
        self,
        type: Literal["all", "user"] = "user",
        *,
        user: Optional[User | dict | str] = None,
    ):
        if type == "all" and user:
            raise TypeError("When `type` is set to `all`, `user` should remain None.")

        if type == "user" and not user:
            raise TypeError("Keyword-only argument `user` was not given.")

        self.type = type
        self.user_id = None
        if type == "user" and user:
            # pass type check
            if isinstance(user, dict):
                self.user_id = user["id"]
            elif isinstance(user, str):
                self.user_id = user
            else:
                self.user_id = user.id

    def to_json(self) -> dict:
        """Converts to a valid JSON."""
        return {"type": self.type, "userId": self.user_id}

    def __repr__(self) -> str:
        return f"Mention(type={self.type!r}, user_id={self.user_id!r})"

    @staticmethod
    def all() -> Mention:
        """Shortcut for an ``@All`` mention."""
        return Mention("all")

    @staticmethod
    def user(user: User) -> Mention:
        """Shortcut for a user mention.

        Args:
            user (:obj:`User`): The user.
        """
        return Mention("user", user=user)

    @staticmethod
    def from_user_id(id: str) -> Mention:
        """Mention a user from its ID, instead of a complete user object.

        Args:
            id (str): The user ID.
        """
        return Mention("user", user={"id": id})

    @staticmethod
    def includes_mentions(
        mentionees: list[Mention], user: BotUser | User | str
    ) -> bool:
        """Check whether a user / the bot is being mentioned in a message or not.

        Args:
            mentionees (list[Mention]): The mentionees of the message.
            user (:obj:`BotUser` | :obj:`User` | str): The user to check for. Could be a user ID or object.
        """
        for mention in mentionees:
            if mention.type == "all":
                return True

            if isinstance(user, str) and mention.user_id == user:
                return True

            if not isinstance(user, str) and mention.user_id == user.id:
                return True

        return False
