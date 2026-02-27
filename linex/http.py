import json
from typing import Any, Optional

import httpx

from .rate_limiting import RateLimit

rr_botInfo = RateLimit.other()

API_ENDPOINT = "https://api.line.me/v2"
DATA_ENDPOINT = "https://api-data.line.me/v2"


async def get_bot_info(client: httpx.AsyncClient) -> dict:
    await rr_botInfo.call()
    resp = await client.get(API_ENDPOINT + "/bot/info")
    return resp.json()


rr_getMemberCount = RateLimit.other()


async def fetch_group_member_count(client: httpx.AsyncClient, group_id: str) -> dict:
    await rr_getMemberCount.call()

    resp = await client.get(
        API_ENDPOINT + f"/bot/group/{group_id}/members/count",
    )
    return resp.json()


rr_getGroupChat = RateLimit.other()


async def fetch_group_chat_summary(
    client: httpx.AsyncClient, group_id: str
) -> dict[str, str]:
    await rr_getGroupChat.call()

    resp = await client.get(API_ENDPOINT + f"/bot/group/{group_id}/summary")
    resp.raise_for_status()
    return resp.json()


async def reply(
    client: httpx.AsyncClient,
    reply_token: str,
    messages: list[dict[str, Any]],
    notificationDisabled: bool,
) -> dict:
    # op(messages)
    resp = await client.post(
        API_ENDPOINT + "/bot/message/reply",
        json={
            "replyToken": reply_token,
            "messages": messages,
            "notificationDisabled": notificationDisabled,
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(
            "error while replying:\n" + json.dumps(resp.json(), indent=2)
        )

    return resp.json()


async def mark_as_read(client: httpx.AsyncClient, mar_token: str):
    resp = await client.post(
        API_ENDPOINT + "/bot/chat/markAsRead",
        json={
            "markAsReadToken": mar_token,
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(
            "error while marking as read:\n" + json.dumps(resp.json(), indent=2)
        )


async def display_loading(
    client: httpx.AsyncClient, chat_id: str, seconds: int | None
) -> dict:
    resp = await client.post(
        API_ENDPOINT + "/chat/loading/start",
        json={"chatId": chat_id, "loadingSeconds": seconds},
    )
    if resp.status_code != 200:
        raise RuntimeError(
            "error while displaying loading:\n" + json.dumps(resp.json(), indent=2)
        )
    return resp.json()


async def push(
    client: httpx.AsyncClient,
    to: str,
    messages: list[dict[str, Any]],
    notificationDisabled: bool,
) -> dict:
    # op(messages)
    resp = await client.post(
        API_ENDPOINT + "/bot/message/push",
        json={
            "to": to,
            "messages": messages,
            "notificationDisabled": notificationDisabled,
        },
    )
    if resp.status_code != 200:
        raise RuntimeError("error while pushing:\n" + json.dumps(resp.json(), indent=2))
    return resp.json()


rr_getUser = RateLimit.other()


async def fetch_user(client: httpx.AsyncClient, user_id: str) -> dict[str, str]:
    await rr_getUser.call()

    resp = await client.get(API_ENDPOINT + f"/bot/profile/{user_id}")
    return resp.json()


async def fetch_location(location: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json"},
        )
        return resp.json()


rr_setWebhookEndpoint = RateLimit.webhook_endpoint()


async def set_webhook_endpoint(client: httpx.AsyncClient, endpoint: str) -> dict:
    await rr_setWebhookEndpoint.call()

    resp = await client.put(
        API_ENDPOINT + "/bot/channel/webhook/endpoint",
        json={"endpoint": endpoint} if endpoint is not None else {},
    )
    return resp.json()


rr_getWebhook = RateLimit.webhook_endpoint()


async def fetch_webhook(client: httpx.AsyncClient) -> dict[str, str | bool]:
    await rr_getWebhook.call()

    resp = await client.get(API_ENDPOINT + "/bot/channel/webhook/endpoint")
    return resp.json()


rr_testWebhook = RateLimit.stats_and_broadcast()


async def test_webhook(
    client: httpx.AsyncClient, endpoint: Optional[str] = None
) -> dict[str, bool | str]:
    await rr_testWebhook.call()

    resp = await client.post(
        API_ENDPOINT + "/bot/channel/webhook/test",
        json={
            "endpoint": endpoint,
        } if endpoint is not None else {},
    )
    return resp.json()


async def fetch_file(client: httpx.AsyncClient, message_id: str):
    url = DATA_ENDPOINT + f"/bot/message/{message_id}/content"

    resp = await client.get(url)

    if resp.status_code == 404:
        raise TypeError("(404) Unknown message ID.")
    elif resp.status_code == 410:
        raise TypeError("(410) Message is gone. (usually caused by unsending)")

    return resp
