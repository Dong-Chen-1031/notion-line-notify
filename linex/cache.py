from collections import deque
from typing import Any, Generic, Literal, TypeAlias, TypeVar, overload

# from .models import Group, MessageContext, User

# K = TypeVar("K")
# V = TypeVar("V")

# T = TypeVar("T")


# class _missing:
#     def __bool__(self) -> Literal[False]:
#         return False


# _MISSING = _missing()
# Maybe: TypeAlias = T | _missing


# class KvCache(Generic[K, V]):
#     __slots__ = ("data", "recents", "threshold")
#     data: dict[K, V]
#     recents: deque[K]
#     threshold: int

#     def __init__(self, default: dict[K, V], *, threshold: Maybe[int] = _MISSING):
#         self.data = default
#         self.recents = deque()
#         self.threshold = threshold or 1000

#     def clear_cache(self):
#         while len(self.data) >= 1000:
#             least_used = self.recents.popleft()
#             self.data.pop(least_used)

#     @overload
#     def get(self, key: K, default: T, /) -> T | V: ...

#     @overload
#     def get(self, key: K, default: Literal[None] = None, /) -> T | None: ...

#     def get(self, key: K, default: T | None = None, /) -> T | V | None:
#         """Gets an item from the cache, if exists."""
#         entry = self.data.get(key, _MISSING)
#         if isinstance(entry, _missing):
#             # notes on typing
#             # currently basedpyright doesn't know the usage of
#             # is MISSING
#             # it marks it as fucking typing error
#             # fuckass motherfucking typing system
#             return default

#         self.recents.append(key)
#         self.clear_cache()
#         return entry

#     def clear(self):
#         self.recents.clear()
#         self.data.clear()


# class InMemoryCache:
#     users: KvCache[str, User]
#     groups: KvCache[str, Group]
#     messages: KvCache[str, MessageContext]

#     def __init__(
#         self,
#         *,
#         users_threshold: Maybe[int] = _MISSING,
#         groups_threshold: Maybe[int] = _MISSING,
#         messages_threshold: Maybe[int] = _MISSING,
#     ):
#         self.users = KvCache(
#             {},
#             threshold=users_threshold,
#         )
#         self.groups = KvCache({}, threshold=groups_threshold)
#         self.messages = KvCache({}, threshold=messages_threshold or 2000)


USERS: dict[str, Any] = {}
GROUPS: dict[str, Any] = {}
MESSAGES: dict[str, Any] = {}

# NOTE: don't import models here (would cause an error)
