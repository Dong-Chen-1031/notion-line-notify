from typing import Any, Optional

import httpx

from ..http import get_group_member_count, push
from .messages import _to_valid_message_objects
from .quick_reply import QuickReplyButton
from .sender import Sender


class Group:
    """Represents a LINE group.

    Args:
        data (dict[str, str]): The group data.
        headers (dict): The authorization headers.
        client (httpx.AsyncClient): The HTTP client.
    """

    __slots__ = ("_group_id", "_group_name", "_picture_url", "_headers", "_client")

    def __init__(self, data: dict[str, str], headers: dict, client: httpx.AsyncClient):
        self._group_id = data["groupId"]
        self._group_name = data["groupName"]
        self._picture_url = data["pictureUrl"]
        self._headers = headers
        self._client = client

    @property
    def id(self) -> str:
        """The group ID."""
        return self._group_id

    @property
    def name(self) -> str:
        """The group name."""
        return self._group_name

    @property
    def picture_url(self) -> str:
        """The group picture (icon) URL."""
        return self._picture_url

    picture = icon = icon_url = picture_url

    async def count(self):
        """Shows the group count."""
        resp = await get_group_member_count(self._headers, self.id)
        return resp["count"]

    async def push_message(
        self,
        *messages: str | Any,
        sender: Optional[Sender] = None,
        quick_replies: Optional[list[QuickReplyButton]] = None,
        notification_disabled: bool = False,
    ):
        """Reply to the message.

        Could only used **once** for each message.

        Args:
            *messages (str | Any): The messages to send.
            sender (:obj:`Sender`, optional): The sender.
            quick_replies (list of :obj:`QuickReplyButton`, optional): List of
                quick reply buttons.
            notification_disabled (bool, optional): Whether to make this message
                silent or not. If ``True``, user will not receive the push
                notification for their device.
        """
        """Sends a push message to the group."""

        valid_messages = _to_valid_message_objects(messages)

        if quick_replies:
            valid_messages[-1] |= {
                "quickReply": {"items": [item.to_json() for item in quick_replies]}
            }

        if sender:
            valid_messages[-1] |= {"sender": sender.to_json()}

        await push(
            self._client,
            self._headers,
            self.id,
            valid_messages,
            notification_disabled,
        )
