from typing import TYPE_CHECKING, Any

import httpx

from .cache import MESSAGES
from .log import logger
from .models import (
    AccountLinkContext,
    AudioMessageContext,
    BaseContext,
    BeaconContext,
    FileMessageContext,
    FollowContext,
    ImageMessageContext,
    JoinContext,
    LeaveContext,
    LocationMessageContext,
    MemberJoinContext,
    MemberLeaveContext,
    MessageContext,
    PostbackContext,
    StickerMessageContext,
    TextMessageContext,
    UnfollowContext,
    UnsendContext,
    VideoMessageContext,
    VideoViewingCompleteContext,
)

if TYPE_CHECKING:
    from linex.application import Client


def add_to_message_cache(
    context: MessageContext,
) -> None:
    """Adds a message context to the cache."""
    MESSAGES[context.id] = context
    if len(MESSAGES) > 1000:
        MESSAGES.pop(next(iter(MESSAGES)))


MESSAGE_CONTEXTS: dict[str, type[MessageContext]] = {
    "text": TextMessageContext,
    "image": ImageMessageContext,
    "video": VideoMessageContext,
    "audio": AudioMessageContext,
    "file": FileMessageContext,
    "location": LocationMessageContext,
    "sticker": StickerMessageContext,
}
OTHER_CONTEXTS: dict[str, type[BaseContext]] = {
    "unsend": UnsendContext,
    "follow": FollowContext,
    "unfollow": UnfollowContext,
    "join": JoinContext,
    "leave": LeaveContext,
    "memberJoined": MemberJoinContext,
    "memberLeft": MemberLeaveContext,
    "postback": PostbackContext,
    "videoPlayComplete": VideoViewingCompleteContext,
    "beacon": BeaconContext,
    "accountLink": AccountLinkContext,
}


async def process(
    cls: Client,
    client: httpx.AsyncClient,
    payload: dict,
) -> None:
    """Process the webhook event payload.

    Args:
        cls (:obj:`Client`): A constructed (initialized) client class.
        client (:obj:`httpx.AsyncClient`): The httpx async client.
        payload (dict): The webhook event payload sent from LINE.
    """
    events: list[dict] = payload["events"]

    if not events:
        settings_link = (
            f"https://manager.line.biz/account/{cls.user.basic_id}/setting/response"
        )
        return logger.log(
            "[blue]Successfully verified![/blue] Next:\n"
            "1. Please flip the 'Use Webhook' switch!\n"
            "2. Turn off auto-reply messages.\n"
            "3. Turn off greeting messages.\n"
            "4. (optional) Allow bot to join group chats.\n\n"
            f"[link={settings_link}]✨ Open Settings[/link]"
        )

    def fulfill_pendings(name: str, context: Any):
        for item in list(cls.pending[name]):
            cls.pending[name][item] = context

    for event in events:
        if event["mode"] == "standby" and cls.ignore_standby:
            continue

        if event["type"] == "message":
            name = event["message"]["type"]
            ctx = MESSAGE_CONTEXTS.get(name)
            if ctx is None:
                logger.warning(f"unknown message type: {name!r} - skipping event")
                continue
            context = ctx(client, event)
            add_to_message_cache(context)

        else:
            ctx = OTHER_CONTEXTS.get(event["type"])
            if ctx is not None:
                name = event["type"]
                context = OTHER_CONTEXTS[event["type"]](client, event)
            else:
                raise NameError(f"unknown event type: {event['type']}")

        fulfill_pendings(name, context)

        await cls.emit(name, context)
