from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .models.context import TextMessageContext


@dataclass
class Command:
    name: str
    func: Callable[..., Awaitable[Any]]
    meta: dict

    async def handle_command(
        self,
        ctx: TextMessageContext,
    ) -> bool:
        if not ctx.text.startswith(self.name):
            return False

        if not self.meta["kw"] and not self.meta["regular"]:
            await self.func(ctx)
            return True

        parts: list[str] = ctx.text[len(self.name + " ") :].split(";")
        args = []
        args.append(ctx)
        kwargs = {}

        for index, part in enumerate(parts):
            if self.meta["kw"] and (index + 1) > len(self.meta["regular"]):
                # keyword-only
                if self.meta.get("kw") and not kwargs:
                    kwargs[self.meta["kw"][0]] = ""

                kwargs[self.meta["kw"][0]] += part + " "
                continue

            name, _type = self.meta["regular"][index]

            if _type not in (str, int, float, bool):
                raise TypeError(
                    f"Command handler {self.func.__name__}:\n"
                    f"Argument '{name}' is not a supported type. "
                    "(From str, int, float, and bool.)"
                )

            args.append(_type(part))

        if kwargs:
            _name = kwargs[self.meta["kw"][0]]
            kwargs[self.meta["kw"][0]] = _name.rstrip()

        await self.func(*args, **kwargs)
        return True
