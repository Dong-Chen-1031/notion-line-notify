from dataclasses import dataclass, field
from typing import Any, Literal, Optional

import httpx

from ..http import get_group_member_count, push
from .messages import _to_valid_message_objects
from .quick_reply import QuickReplyButton
from .sender import Sender


@dataclass
class Group:
    """Represents a LINE group.

    Args:
        client (httpx.AsyncClient): The HTTP client.
        headers (dict): The authorization headers.
        data (dict[str, str]): The group data.
    """

    client: httpx.AsyncClient
    headers: dict[str, str]
    payload: dict[str, Any]

    id: str = field(init=False)
    """The group ID."""

    name: str = field(init=False)
    """The group name."""

    picture_url: str = field(init=False)
    """The group picture (icon) URL."""

    def __post_init__(self):
        self.id = self.payload["groupId"]
        self.name = self.payload["groupName"]
        self.picture_url = self.payload["pictureUrl"]

    async def count(self) -> int:
        """Shows the group members count."""
        resp = await get_group_member_count(self.headers, self.id)
        return resp["count"]

    async def push_message(
        self,
        *messages: str | Any,
        sender: Optional[Sender] = None,
        quick_replies: Optional[list[QuickReplyButton]] = None,
        notification_disabled: bool = False,
    ):
        """Send a push message to the group.

        Args:
            *messages (str | Any): The messages to send.
            sender (:obj:`Sender`, optional): The sender.
            quick_replies (list of :obj:`QuickReplyButton`, optional): List of
                quick reply buttons.
            notification_disabled (bool, optional): Whether to make this message
                silent or not. If ``True``, user will not receive the push
                notification for their device.
        """

        valid_messages = _to_valid_message_objects(messages)

        if quick_replies:
            valid_messages[-1] |= {
                "quickReply": {"items": [item.to_json() for item in quick_replies]}
            }

        if sender:
            valid_messages[-1] |= {"sender": sender.to_json()}

        await push(
            self.client,
            self.headers,
            self.id,
            valid_messages,
            notification_disabled,
        )


@dataclass(frozen=True)
class SourceGroup:
    """Represents a regular LINE group, but with limited data.

    The data usually comes from events.
    """

    type: Literal["group"]

    id: str
    """ID of the source group chat."""

    @staticmethod
    def from_json(data: dict[str, str]) -> "SourceGroup":
        return SourceGroup(
            type="group",
            id=data["groupId"],
        )
