from typing import Any

from httpx import AsyncClient

USERS: dict[str, Any] = {}
GROUPS: dict[str, Any] = {}
MESSAGES: dict[str, Any] = {}
HTTP_CLIENT: AsyncClient = AsyncClient()

# NOTE: don't import models here (would cause an error)
