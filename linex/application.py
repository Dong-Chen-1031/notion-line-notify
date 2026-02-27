from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import socket
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from inspect import iscoroutinefunction as is_coro
from typing import Any, Callable, Literal, Optional

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from linex.command import Command
from linex.models.context import TextMessageContext

from .cache import GROUPS, MESSAGES, USERS
from .exceptions import Unknown
from .http import (
    fetch_group_chat_summary,
    fetch_user,
    fetch_webhook,
    get_bot_info,
    push,
    set_webhook_endpoint,
    test_webhook,
)
from .log import logger
from .models import BotUser, Group, PostbackContext, User
from .models.group import SourceGroup
from .models.messages import to_valid_message_objects
from .models.quick_reply import QuickReplyButton
from .models.sender import Sender
from .models.user import SourceUser
from .processing import process
from .utils import get_params_with_types


class Client:
    """Represents a LINE bot.

    Args:
        channel_secret (:obj:`str`, optional): The channel secret, used to identify
            whether a request is sent by LINE or not. If not given, reads an
            environment variable named ``LINE_CHANNEL_SECRET`` instead.
        channel_access_token (:obj:`str`, optional): The ƒchannel access token, used for
            almost every single client-request. DO NOT LEAK IT.
            If not given, reads an environment variable named ``LINE_CHANNEL_ACCESS_TOKEN``
            instead.
        dev (:obj:`bool`, optional): Whether to enable dev mode or not. It's especially
            useful when you're writing an extension for Linex.
        ignore_standby (bool, optional): Whether to ignore the ``standby`` status.
        disable_logs (bool, optional): Whether to disable all logs or not.

    Attributes:
        channel_secret (str): The channel secret.
        channel_access_token (str): The channel access token.
        app (FastAPI): The running FastAPI application.
        user (BotUser): The bot user.
        headers (dict of str: str): The authorization headers.
        is_ready (bool): Whether the bot is ready or not.
        handlers (dict of str: list of :obj:`Callable`): The registered event handlers.
    """

    __slots__ = (
        "channel_secret",
        "channel_access_token",
        "app",
        "client",
        "user",
        "headers",
        "is_ready",
        "ignore_standby",
        "webhook",
        "_commands",
        "start_kwargs",
    )

    app: FastAPI
    client: httpx.AsyncClient
    channel_secret: str
    channel_access_token: str
    handlers: dict[str, list[Callable[..., Any]]] = {
        "ready": [],
        "text": [],
        "image": [],
        "audio": [],
        "file": [],
        "location": [],
        "sticker": [],
        "video": [],
        "unsend": [],
        "follow": [],
        "unfollow": [],
        "join": [],
        "leave": [],
        "member_join": [],
        "member_leave": [],
        "postback": [],
        "video_complete": [],
        "beacon": [],
        "account_link": [],
        "device_link": [],
        "device_unlink": [],
        "scenario_result": [],
    }
    pending: dict[str, dict[str, Any]] = {name: {} for name in list(handlers)}
    headers: dict
    is_ready: bool
    user: BotUser
    ignore_standby: bool
    webhook: ApplicationWebhook
    _commands: dict[str, Command]

    def __init__(
        self,
        channel_secret: Optional[str] = None,
        channel_access_token: Optional[str] = None,
        *,
        dev: bool = False,
        ignore_standby: bool = True,
        disable_logs: bool = False,
    ) -> None:
        self.channel_secret = channel_secret or os.environ["LINE_CHANNEL_SECRET"]
        self.channel_access_token = (
            channel_access_token or os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
        )
        self.headers = {"Authorization": f"Bearer {self.channel_access_token}"}

        self.is_ready = False
        self.ignore_standby = ignore_standby

        if disable_logs:
            logger.disabled = True

        self.client = client = httpx.AsyncClient(headers=self.headers)
        self.app = app = FastAPI(lifespan=self.lifespan)
        self._commands = {}
        self.start_kwargs = {}

        @app.get("/")
        async def get_index():
            return "linex is happy"

        @app.post("/")
        async def webhook(request: Request):
            body = await request.body()
            hash = hmac.new(
                self.channel_secret.encode("utf-8"), body, hashlib.sha256
            ).digest()
            valid_signature = base64.b64encode(hash)

            line_signature = request.headers.get("X-Line-Signature", "").encode("utf-8")
            result: bool = hmac.compare_digest(line_signature, valid_signature)

            if not result:
                logger.routing.fail("POST", "/", "invalid signature")
                return JSONResponse({"message": "invalid webhook"}, 400)

            payload = await request.json()
            n_events = len(payload["events"])

            logger.routing.ok(
                "POST",
                "/",
                "payload [d white]({n} event{s})[/d white]".format(
                    n=n_events, s="s" if n_events > 1 or n_events == 0 else ""
                ),
            )

            if dev:
                logger.print(payload)

            try:
                await process(self, client, payload)
            except Exception as err:
                raise err
            return {"message": "happy birthday"}

    def event(self, handler: Callable[..., Any]) -> None:
        """Acts an event handler decorator.

        Args:
            handler (Callable): The event handler in coroutine.

        Example:
            .. code-block:: python

               @client.event
               async def on_ready():
                   print("bot is ready!")
        """
        name = handler.__name__[len("on_") :]
        if name not in self.handlers:
            self.handlers[name] = []

        self.handlers[name].append(handler)

    def listen(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Listens to a specific event.

        Acts as a decorator.

        Args:
            name (str): The event name. Do not prefix with ``on_``.

        Example:
            .. code-block:: python

               @client.listen("ready")
               async def ready_handler():
                   print("bot is ready!")
        """

        def wrapper(handler: Callable[..., Any]) -> Callable[..., Any]:
            if name not in self.handlers:
                self.handlers[name] = []

            self.handlers[name].append(handler)
            return handler

        return wrapper

    async def process_commands(self, ctx: TextMessageContext) -> bool:
        """Processes commands.

        (coroutine)

        Args:
            ctx (TextMessageContext): The text message context.
        """

        return any([await cmd.handle_command(ctx) for cmd in self._commands.values()])

    async def emit(self, name: str, *data) -> None:
        """Emits a specific event.

        *(coroutine)*

        Args:
            name (str): The event name.
            *data: Any data.

        Example:
            .. code-block:: python

               @client.event
               async def on_custom_event(
                   important: str,
                   data: float
               ):
                   ...

               await client.emit(
                   "custom_event",
                   "some data 1",
                   31.123
               )
        """
        # for handler in self.handlers[name]:
        #     if not handler:
        #         continue

        #     await handler(*data)

        async def do_event_safe(handler, *data):
            try:
                await handler(*data)
            except Exception:
                logger.routing.fail(
                    "EVENT", name, f"an error occurred in handler {handler.__name__}"
                )
                logger.print_exception()

        handlers = [
            do_event_safe(handler, *data) for handler in self.handlers[name] if handler
        ]

        # for command
        if name == "text" and not handlers:
            handlers.append(do_event_safe(self.process_commands, *data))

        await asyncio.gather(*handlers, return_exceptions=True)

    def run(self, **kwargs):
        """Runs the bot.

        Args:
            **kwargs: Arguments for ``uvicorn.run``.
        """
        self.webhook = ApplicationWebhook(self.client)
        self.start_kwargs = {
            "app": self.app,
            "host": "0.0.0.0",
            "port": 8080,
            "log_level": logging.WARNING,
            **kwargs,
        }
        print(self.start_kwargs)
        uvicorn.run(**self.start_kwargs)

    @asynccontextmanager
    async def lifespan(self, _: FastAPI):
        logger.print()
        logger.print("  [green]linex[/green] [blue]v1 beta[/blue] running at:")
        logger.print()
        logger.print(
            f"  :computer: local:   http://{self.start_kwargs.get('host', 'localhost')}:{self.start_kwargs.get('port', 8080)}"
        )

        if (slug := os.environ.get("REPL_SLUG")) and (
            owner := os.environ.get("REPL_OWNER")
        ):
            logger.print(
                f"  :globe_with_meridians: network: https://{slug}.{owner}.repl.co"
            )
        else:
            try:
                network_host = socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                network_host = "127.0.0.1"
            logger.print(
                f"  :globe_with_meridians: network: http://{network_host}:{self.start_kwargs.get('port', 8080)}"
            )
        logger.print()

        self.user = BotUser.from_json(await get_bot_info(self.client))
        USERS[self.user.id] = self.user

        self.is_ready = True
        await self.emit("ready")

        yield

    # ===============
    # utils
    # ===============

    def get_user(self, user_id: str) -> BotUser | User:
        """Gets a user from their ID.

        (cache)

        Args:
            user_id (str): The user ID.
        """
        user = USERS.get(user_id)

        if not user:
            raise Unknown(
                "Unknown user. This user hasn't interacted with this bot yet."
            )

        return user

    def get_group(self, group_id: str) -> Group:
        """Gets a group from its ID.

        (cache)

        Args:
            group_id (str): The group ID.
        """
        group = GROUPS.get(group_id)

        if not group:
            raise Unknown(
                "Unknown group. This group hasn't interacted with this bot yet."
            )

        return group

    def get_message(self, message_id: str) -> Any:
        """Gets a message from its ID.

        (cache)

        Args:
            message_id (str): The message ID.
        """
        message = MESSAGES.get(message_id)

        if not message:
            raise Unknown(f"Unknown message with ID {message_id}.")

        return message

    def clear_cache(self) -> None:
        """Clears all of the cache.

        This action is NOT revertable.
        """
        # lol funni joke
        victims = (GROUPS, USERS, MESSAGES)
        for target in victims:
            target.clear()

    def clear_cache_for(self, *targets: Literal["groups", "users", "messages"]):
        """Clear the cache for specific targets.

        Example:
        ```python
        clear_cache_for("messages")
        clear_cache_for("groups", "users", "messages")
        ```
        """
        victims = {"groups": GROUPS, "users": USERS, "messages": MESSAGES}
        for target in targets:
            victims[target].clear()

    async def wait_for(
        self,
        name: str,
        *,
        check: Callable[[Any], bool] = lambda _: True,
        timeout: Optional[int] = None,
    ):
        """Waits for a specific event (without ``on_``).

        Args:
            name (str): The event name. (e.g., ``text``)
            check (:obj:`Callable`, optional): A checker function.
            timeout (int, optional): Assign a timeout, if needed.

        Raises:
            asyncio.TimeoutError: Timeout exceeded (if given).
        """
        _id = str(uuid.uuid4())
        self.pending[name][_id] = None
        result: Any = None
        elapsed: float = 0
        logger.print(self.pending)

        while not result:
            _pre_result = self.pending[name][_id]

            # the reason we're ignoring this is because that
            # the check function should only accept context
            # ...not a bool, so do not wrap it outside.

            if _pre_result is not None:
                if not check(_pre_result):
                    continue
                else:
                    result = _pre_result

            await asyncio.sleep(0.01)
            elapsed += 0.01

            if timeout and elapsed >= timeout:
                raise asyncio.TimeoutError(f"Timeout while waiting for {name!r} event.")

        del self.pending[name][_id]
        return result

    def postback(self, data: str) -> Callable[[Callable[..., Any]], Callable]:
        """Handles postback events.

        Acts as a decorator.

        Args:
            data (str): The prefix of the postback data (custom ID).

        Example:
            .. code-block :: python
                my_data = linex.utils.postback_data("handling", 1, "happy")

                @client.postback("handling")
                async def handler(
                    ctx: linex.PostbackContext,
                    num: int,
                    message: str
                ):
                    ...
        """

        def wrapper(func: Callable[..., Any]):
            if not is_coro(func):
                raise TypeError(
                    f"Function {func.__name__} is not a coroutine (async) function."
                )

            meta = get_params_with_types(func)

            @self.event
            async def on_postback(ctx: PostbackContext):
                parts: list[str] = ctx.data[len(data + ";") :].split(";")
                args = []
                args.append(ctx)
                kwargs = {}

                for index, part in enumerate(parts):
                    if meta["kw"] and (index + 1) > len(meta["regular"]):  # type: ignore
                        # keyword-only
                        if meta.get("kw") and not kwargs:
                            kwargs[meta["kw"][0]] = ""

                        kwargs[meta["kw"][0]] += part
                        continue

                    name, _type = meta["regular"][index]  # type: ignore

                    if _type not in (str, int, float, bool):
                        raise TypeError(
                            f"Postback handler {func.__name__}:\n"
                            f"Argument '{name}' is not a supported type. "
                            "(From str, int, float, and bool.)"
                        )

                    args.append(_type(part))

                if kwargs:
                    _name = kwargs[meta["kw"][0]]  # type: ignore
                    kwargs[meta["kw"][0]] = meta["kw"][1](_name)  # type: ignore

                await func(*args, **kwargs)

            return func

        return wrapper

    async def send_message(
        self,
        to: str | Group | User,
        *messages: str | Any,
        sender: Optional[Sender] = None,
        quick_replies: Optional[list[QuickReplyButton]] = None,
        notification_disabled: bool = False,
    ):
        """Sends a push message to either a group or a user.

        Args:
            *messages (str | Any): The messages to send.
            sender (:obj:`Sender`, optional): The sender.
            quick_replies (list of :obj:`QuickReplyButton`, optional): List of
                quick reply buttons.
            notification_disabled (bool, optional): Whether to make this message
                silent or not. If ``True``, user will not receive the push
                notification for their device.
        """
        if isinstance(to, str):
            to_id = to
        elif isinstance(to, Group | User):
            to_id = to.id
        else:
            raise TypeError("Argument 'to' must be of type str, Group, or User.")

        valid_messages = to_valid_message_objects(messages)

        if quick_replies:
            valid_messages[-1] |= {
                "quickReply": {"items": [item.to_json() for item in quick_replies]}
            }

        if sender:
            valid_messages[-1] |= {"sender": sender.to_json()}

        await push(
            self.client,
            to_id,
            valid_messages,
            notification_disabled,
        )

    def command(
        self, *, name: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Registers a command.

        Acts as a decorator.

        Args:
            name (str): The command name.
        """

        def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
            if name in self._commands:
                raise ValueError(f"Command already exists: {name!r}")

            if not is_coro(func):
                raise TypeError(
                    f"Function {func.__name__} is not a coroutine (async) function."
                )

            meta = get_params_with_types(func)

            self._commands[name] = Command(name, func, meta)

            return func

        return wrapper

    async def fetch_user(self, suser: str | SourceUser) -> User:
        """Fetches the author."""
        user = User.from_json(
            await fetch_user(self.client, suser if isinstance(suser, str) else suser.id)
        )
        USERS[user.id] = user

        return user

    async def fetch_group(self, sgroup: str | SourceGroup) -> Group:
        """Fetches group information."""
        group = Group(
            self.client,
            await fetch_group_chat_summary(
                self.client,
                sgroup if isinstance(sgroup, str) else sgroup.id,
            ),
        )
        GROUPS[group.id] = group
        return group


@dataclass(frozen=True)
class ApplicationWebhook:
    client: httpx.AsyncClient

    async def set_endpoint(self, endpoint: str) -> None:
        """Sets the webhook endpoint URL.

        (coroutine)

        It may take up to 1 minute for changes to take place due to caching.

        Rate limit: 1,000 requests per minute (exceeding preventable)

        Args:
            endpoint (str): The endpoint. Must be a valid HTTPS URL.
        """
        await set_webhook_endpoint(self.client, endpoint)

    async def get_info(self) -> tuple[str, bool]:
        """Gets information on a webhook endpoint.

        (coroutine)

        Returns:
            tuple[str, bool]: A tuple represents (``url``, ``active?``). ``active?``
                represents whether it's active (verified) or not.
        """
        resp: dict[str, Any] = await fetch_webhook(self.client)
        endpoint: str = resp["endpoint"]
        active: bool = resp["active"]

        return endpoint, active

    async def test_endpoint(
        self, endpoint: Optional[str] = None
    ) -> dict[str, str | bool]:
        """Checks if the configured webhook endpoint can receive a test webhook event.

        (coroutine)

        Args:
            endpoint (str, optional): The webhook URL to be validated. If not given,
                tests the webhook endpoint that's already set to the channel.

        Returns:
            dict[str, str | bool]: A JSON output. See the example.

        Example:
            .. code-block :: python
                await client.webhook.test_endpoint()
                # returns (if success):
                # {
                #     "success": True,
                #     "reason": "OK",
                #     "detail": "200"
                # }
                #
                # returns (if failed, example):
                # {
                #     "success": False,
                #     "reason": "COULD_NOT_CONNECT",
                #     "detail": "TLS handshake failure: https://example.com"
                # }
        """
        resp: dict = await test_webhook(self.client, endpoint)

        return {
            "success": resp["success"],
            "reason": resp["reason"],
            "detail": resp["detail"],
        }
