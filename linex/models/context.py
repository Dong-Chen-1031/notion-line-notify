# ruff: noqa: E501
from __future__ import annotations

import mimetypes
import time
import uuid
from dataclasses import dataclass, field
from typing import IO, Any, Literal, Optional

import httpx

from ..cache import GROUPS, USERS
from ..exceptions import CannotReply
from ..http import (
    display_loading,
    fetch_file,
    fetch_group_chat_summary,
    fetch_user,
    mark_as_read,
    reply,
)
from .emoji import Emoji
from .group import Group, SourceGroup
from .mention import Mention
from .messages import to_valid_message_objects
from .multi_person import SourceMultiPerson
from .quick_reply import QuickReplyButton
from .sender import Sender
from .user import BotUser, SourceUser, User


@dataclass
class BaseContext:
    """Represents a base context."""

    event_type: str = field(init=False)

    event_id: str = field(init=False)
    """Webhook event ID."""

    is_redelivery: bool = field(init=False)
    """Whether this event is a webhook redelivery."""

    timestamp: int = field(init=False)
    """The timestamp in seconds.

    Could be used to calculate the ping.
    """

    source: dict[str, str] | None = field(init=False)
    """The message source.

    Could be a user, group chat, or multi-person chat.

    This property won't be included in the account link event if linking the account has failed.
    """

    reply_token: str | None = field(init=False)
    """The reply token.

    May not be present if ``mode`` is ``standby``
    """

    mode: Literal["active", "standby"] = field(init=False)
    """Channel state.

    * ``active``: The channel is active. You can send a reply message or
        push message, etc.
    * ``standby``: The channel is waiting for the
        `module <https://developers.line.biz/en/docs/partner-docs/module/>`_ to reply.
        At this point, you cannot reply the message.
    """

    client: httpx.AsyncClient
    payload: dict[str, Any]

    def __post_init__(self):
        self.event_type = self.payload["type"]
        self.event_id = self.payload["webhookEventId"]
        self.is_redelivery = self.payload["deliveryContext"]["isRedelivery"]
        self.timestamp = self.payload["timestamp"] / 1000
        self.source = self.payload.get("source")
        self.reply_token = self.payload.get("replyToken")
        self.mode = self.payload["mode"]

    @property
    def is_active(self) -> bool:
        """A shortcut for detecting whether the current mode is active.

        Example:

        ```python
        if not ctx.is_active:
            return
        ```
        """
        return self.mode == "active"

    @property
    def source_type(self) -> Literal["user", "group", "room"]:
        """Checks the chat (source) type.

        This property will cause an error if used on failed account link events.
        """
        assert self.source is not None
        return self.source["type"]  # pyright: ignore [reportReturnType]

    def source_as_group(self) -> SourceGroup:
        """Casts the source as a group chat.

        Raises an error if the source type is not `group`.
        """
        assert self.source is not None and self.source_type == "group"
        return SourceGroup.from_json(self.source)

    def source_as_user(self) -> SourceUser:
        """Casts the source as a user.

        Raises an error if the source type is not `user`.
        """
        assert self.source is not None and self.source_type == "user"
        return SourceUser.from_json(self.source)

    def source_as_multi_person(self) -> SourceMultiPerson:
        """Casts the source as a multi-person chat.

        Raises an error if the source type is not `room`.
        """
        assert self.source is not None and self.source_type == "room"
        return SourceMultiPerson.from_json(self.source)

    @property
    def source_user(self) -> SourceUser:
        """The source user object."""
        assert self.source is not None
        return SourceUser.from_json(self.source)

    @property
    def source_group(self) -> SourceGroup:
        """The source group object."""
        assert self.source is not None
        return SourceGroup.from_json(self.source)

    @property
    def source_multi_person(self) -> SourceMultiPerson:
        """The source multi-person chat object."""
        assert self.source is not None
        return SourceMultiPerson.from_json(self.source)

    async def fetch_user(self) -> User:
        """Fetches the author. (coroutine)"""
        assert self.source is not None

        author = User.from_json(await fetch_user(self.client, self.source["userId"]))
        USERS[author.id] = author

        return author

    async def fetch_group(self) -> Group:
        """Fetches group information."""
        assert self.source is not None

        if self.source_type != "group":
            raise TypeError("This is not a group chat.")

        group = Group(
            self.client,
            await fetch_group_chat_summary(self.client, self.source["groupId"]),
        )
        GROUPS[group.id] = group
        return group

    async def display_loading(self, seconds: int | None):
        """Display a loading animation in one-on-one chats between users and LINE Official Accounts.

        The loading animation will automatically disappear after the specified number of seconds (5 to 60 seconds)
        has elapsed or when a new message arrives from your LINE Official Account.

        The loading animation is only displayed when the user is viewing the chat screen with your LINE Official Account.
        If you request to display the loading animation when the user isn't viewing the chat screen, no notification will
        be displayed. Even if the user opens the chat screen later, the animation won't be displayed.

        If you request to display the loading animation again while it is still visible, the animation will continue to
        be displayed and the time until it disappears will be overridden by the number of seconds specified in the second
        request.

        Args:
            seconds (int, optional): The number of seconds. Should be between 5-60 (inclusive) and should be
                divisible by 5. Defaults to 20.
        """
        assert self.source_type == "user"
        if seconds is not None:
            assert 5 <= seconds <= 60 and seconds % 5 == 0, (
                "specified duration does not match requirement; see docs"
            )

        await display_loading(self.client, self.source_as_user().id, seconds)

    defer = display_loading


@dataclass
class RepliableContext(BaseContext):
    """A repliable context."""

    replied: bool = False
    """Whether the message has been replied."""

    async def reply(
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
        if not self.reply_token:
            raise TypeError("Reply error was not provided, check `ctx.state`.")

        if time.time() - self.timestamp > 60 * 20:
            raise CannotReply(
                "It's been more than 20 minutes since the event occurred; "
                "you cannot reply to this interaction anymore."
            )

        if self.replied:
            raise CannotReply("This interaction has already been replied.")

        valid_messages = to_valid_message_objects(messages)

        if quick_replies:
            valid_messages[-1] |= {
                "quickReply": {"items": [item.to_json() for item in quick_replies]}
            }

        if sender:
            valid_messages[-1] |= {"sender": sender.to_json()}

        self.replied = True
        await reply(
            self.client,
            self.reply_token,
            valid_messages,
            notification_disabled,
        )

    send = respond = reply


@dataclass
class MessageContext(RepliableContext):
    """A message.

    A repliable context with the `id` field from the message.
    """

    id: str = field(init=False)
    """The ID of the message."""

    mark_as_read_token: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.id = self.payload["message"]["id"]
        self.mark_as_read_token = self.payload["message"]["markAsReadToken"]

    async def mark_as_read(self):
        """Marks this message as read."""
        await mark_as_read(
            self.client,
            self.mark_as_read_token,
        )


@dataclass
class TextMessageContext(MessageContext):
    text: str = field(init=False)
    """The text content."""

    emojis: list[Emoji] = field(init=False)
    """List of emojis.

    May not be present.
    """

    mentions: list[Mention] = field(init=False)
    """Returns a list of mentions in the message."""

    def __post_init__(self):
        super().__post_init__()

        msg = self.payload["message"]
        self.text = msg["text"]
        self.emojis = [
            Emoji(
                emoji["productId"],
                emoji["emojiId"],
            )
            for emoji in msg.get("emojis", [])
        ]
        self.mentions = [
            Mention(
                mention["type"],
                user=mention.get("userId"),
            )
            for mention in msg.get("mention", {}).get("mentionees", [])
        ]

    @property
    def text_with_emojis(self) -> str:
        """Returns text, but with the Linex LINE emoji format.

        For example:
        .. code-block ::
            [emoji id](product id)
        """
        emojis = [emoji.to_json() for emoji in self.emojis]
        return Emoji.fit_on_texts(self.text, emojis)

    def mentioned(self, user: str | User | BotUser) -> bool:
        """Checks whether a user is mentioned in a message or not.

        Args:
            user (:obj:`BotUser` | :obj:`User` | str): The user to check for. Could be a user ID or object.
        """
        return Mention.includes_mentions(self.mentions, user)


@dataclass
class MediaMessageContext(MessageContext):
    """Downloadable media context."""

    content_provider: dict[
        Literal["type", "originalContentUrl", "previewImageUrl"], str
    ] = field(init=False)
    """The content provider of the message.

    `Reference <https://developers.line.biz/en/reference/messaging-api/#wh-image>`_
    """

    def __post_init__(self):
        super().__post_init__()
        self.content_provider = self.payload["message"]["contentProvider"]

    async def download(
        self,
        file: str | IO | None = None,
        *,
        disable_string_parsing: bool = False,
    ) -> str:
        """Downloads the file.

        In the ``fn``, use ``${random}`` to use a random filename, ``${ext}``
        for the extension name (the dot is included).

        Args:
            fn (str, optional): The filename or path.
            disable_string_parsing (bool, optional): Whether to disable string parsing.
                See the note.

        Returns:
            str: The filename or path. If provided an IO as `file`, returns a blank string.
        """
        if self.content_provider["type"] == "line":
            resp = await fetch_file(self.client, self.id)

        else:
            resp = await self.client.get(self.content_provider["originalContentUrl"])

            if resp.status_code != 200:
                raise RuntimeError(
                    "This external resource cannot be reached. (status code: %i)"
                    % resp.status_code
                )

        extension = mimetypes.guess_extension(resp.headers["Content-Type"])
        if isinstance(file, str) or file is None:
            file = file or str(uuid.uuid4()) + (extension or "")

            if not disable_string_parsing:
                file = file.replace("${random}", str(uuid.uuid4())).replace(
                    "${ext}", extension or ""
                )

            with open(file, "wb") as f:
                f.write(resp.content)

            return file
        else:
            file.write(resp.content)
            return ""


@dataclass
class ImageMessageContext(MessageContext):
    image_set: dict[str, str | int] | None = field(init=False)
    """The image set.

    May be None.

    `Reference <https://developers.line.biz/en/reference/messaging-api/#wh-image>`_
    """

    def __post_init__(self):
        super().__post_init__()
        msg = self.payload["message"]
        self.image_set = msg.get("imageSet")


@dataclass
class VideoMessageContext(MediaMessageContext):
    duration: int | None = field(init=False)
    """Duration of the video file. (milliseconds).

    May not always include.
    """

    def __post_init__(self):
        super().__post_init__()
        self.duration = self.payload["message"].get("duration")


@dataclass
class AudioMessageContext(MediaMessageContext):
    duration: int | None = field(init=False)
    """Duration of the audio file. (milliseconds).

    May not always include.
    """

    def __post_init__(self):
        super().__post_init__()
        self.duration = self.payload["message"].get("duration")


@dataclass
class FileMessageContext(MediaMessageContext):
    file_name: str = field(init=False)
    """The file name."""

    file_size: int = field(init=False)
    """The file size in bytes."""

    def __post_init__(self):
        super().__post_init__()
        msg = self.payload["message"]
        self.file_name = msg["fileName"]
        self.file_size = msg["fileSize"]


@dataclass
class LocationMessageContext(MessageContext):
    title: str | None = field(init=False)
    """The title.

    May not be present.
    """

    address: str | None = field(init=False)
    """The address.

    May not be present.
    """

    latitude: float = field(init=False)
    longitude: float = field(init=False)

    def __post_init__(self):
        super().__post_init__()

        msg = self.payload["message"]
        self.title = msg.get("title")
        self.address = msg.get("address")
        self.latitude = msg["latitude"]
        self.longitude = msg["longitude"]


@dataclass
class StickerMessageContext(MessageContext):
    package_id: str = field(init=False)
    sticker_id: str = field(init=False)
    sticker_resource_type: Literal[
        "STATIC",
        "ANIMATION",
        "SOUND",
        "ANIMATION_SOUND",
        "POPUP",
        "POPUP_SOUND",
        "CUSTOM",
        "MESSAGE",
        #'NAME_TEXT',        (deprecated)
        #'PER_STICKER_TEXT'  (deprecated)
    ] = field(init=False)

    keywords: list[str] | None = field(init=False)
    """The keywords to describe the sticker."""

    text: str | None = field(init=False)
    """The message text.

    Only available when ``type`` is ``MESSAGE``.
    """

    def __post_init__(self):
        super().__post_init__()
        msg = self.payload["message"]
        self.package_id = msg["packageId"]
        self.sticker_id = msg["stickerId"]
        self.sticker_resource_type = msg["stickerResourceType"]
        self.keywords = msg.get("keywords")
        self.text = msg.get("text")


@dataclass
class UnsendContext(BaseContext):
    message_id: str = field(init=False)
    """The unsent message ID."""

    def __post_init__(self):
        super().__post_init__()
        self.id = self.payload["unsend"]["messageId"]


@dataclass
class FollowContext(RepliableContext):
    """Represents a follow event context when your LINE Official Account is added as a friend or unblocked."""


@dataclass
class UnfollowContext(BaseContext):
    """Event object for when your LINE Official Account is blocked."""


@dataclass
class JoinContext(RepliableContext):
    """A join event is triggered at different times for group chats and multi-person chats."""


@dataclass
class LeaveContext(BaseContext):
    """Event object for when a user removes your LINE Official Account from a group chat
    or when your LINE Official Account leaves a group chat or multi-person chat.
    """


@dataclass
class MemberJoinContext(RepliableContext):
    """Event object for when a user joins a group chat or multi-person chat that the
    LINE Official Account is in.
    """

    members: list[SourceUser] = field(init=False)
    """Users who joined.

    Array of source user objects.
    """

    def __post_init__(self):
        super().__post_init__()
        self.members = [
            SourceUser.from_json(member) for member in self.payload["joined"]["members"]
        ]


@dataclass
class MemberLeaveContext(BaseContext):
    """Event object for when a user leaves a group chat or multi-person chat that the
    LINE Official Account is in. (Cannot reply)
    """

    members: list[SourceUser] = field(init=False)
    """Users who joined.

    Array of source user objects.
    """

    def __post_init__(self):
        super().__post_init__()
        self.members = [
            SourceUser.from_json(member) for member in self.payload["left"]["members"]
        ]


@dataclass
class PostbackContext(RepliableContext):
    """Event object for when a user joins a group chat or multi-person chat that the
    LINE Official Account is in.
    """

    data: str = field(init=False)
    """The postback data (developer-defined custom ID)."""

    params: dict[str, Any] = field(init=False)
    """Postback parameters for date-time selection or rich menu switch action."""

    def __post_init__(self):
        super().__post_init__()
        self.data = self.payload["postback"]["data"]
        self.params = self.payload["postback"]["params"]

    @property
    def datetime(self) -> str | None:
        """The datetime. Only valid when this is `DatetimePicker`-triggered."""
        return self.params.get("datetime")

    @property
    def new_rich_menu_alias_id(self) -> str | None:
        """The new rich menu alias ID after tapping the action.

        Only valid when this is `RichMenuSwitch`-triggered.
        """
        return self.params.get("newRichMenuAliasId")


@dataclass
class VideoViewingCompleteContext(RepliableContext):
    """Event for when a user finishes viewing a video at least once with the specified
    `tracking_id` sent by the LINE Official Account.

    A video viewing complete event doesn't necessarily indicate the number of
    times a user has watched a video.
    Watching a video multiple times in a single session in a chat room doesn't
    result in a duplicate event. However, if you close the chat room and reopen
    it to watch the video again, the event may reoccur.
    """

    tracking_id: str = field(init=False)
    """ID used to identify a video.

    Returns the same value as the one assigned to the video message.
    """

    def __post_init__(self):
        super().__post_init__()
        self.tracking_id = self.payload["videoPlayComplete"]["trackingId"]


@dataclass
class BeaconContext(RepliableContext):
    """Event object for when a user enters the range of a LINE Beacon.

    You can reply to beacon events.

    `LINE Beacon <https://developers.line.biz/en/docs/messaging-api/using-beacons/>`_
    """

    hardware_id: str = field(init=False)
    """Hardware ID of the beacon that was detected."""

    beacon_event_type: Literal["enter", "banner", "stay"] = field(init=False)
    """Type of beacon event:

    * `enter`: Entered beacon's reception range.
    * `banner`: Tapped beacon banner.
    * `stay`: The user is within the range of the beacon's reception.
        This event is sent repeatedly at a minimum interval of 10 seconds.
    """

    device_message: str | None = field(init=False)
    """Device message of beacon that was detected.

    This message consists of
    data generated by the beacon to send notifications to bot servers.

    Only included in webhook events from devices that support the
    "device message" property.
    """

    def __post_init__(self):
        super().__post_init__()
        beacon = self.payload["beacon"]
        self.hardware_id = beacon["hwid"]
        self.type = beacon["type"]
        self.device_message = beacon.get("dm")


@dataclass
class AccountLinkContext(RepliableContext):
    """Event object for when a user has linked their LINE account with a provider's
    service account. You can reply to account link events.

    If the link token has expired or has already been used, no webhook event will
    be sent and the user will be shown an error.
    """

    result: Literal["ok", "failed"] = field(init=False)
    """One of the following values to indicate whether linking the account
    was successful or not:

    * ``ok``: Indicates linking the account was successful.
    * ``failed``: Indicates linking the account failed for any reason, such as due
        to a user impersonation.

    You cannot reply to the user if linking the account has failed.
    """

    nounce: str = field(init=False)
    """Specified nonce (number used once) when verifying the user ID.

    For more information, see Generate a nonce and redirect the user to the LINE Platform in the Messaging API documentation.

    `Generate a nonce and redirect the user to the LINE Platform <https://developers.line.biz/en/docs/messaging-api/linking-accounts/#step-four-verifying-user-id>`_
    """

    def __post_init__(self):
        super().__post_init__()
        link = self.payload["link"]
        self.result = link["result"]
        self.nounce = link["nounce"]
