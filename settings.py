import os

from dotenv import load_dotenv

load_dotenv()

DEV_MODE: bool = os.getenv("DEV_MODE", "False").lower() in ("true", "1", "t")

if DEV_MODE:
    load_dotenv(".env.dev", override=True)

GROUP_ID: str = os.getenv("GROUP_ID", "")

NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "")

GC_TOKEN_PATH: str = os.getenv("GC_TOKEN_PATH", "keys/token.json")

GC_CREDENTIALS_PATH: str = os.getenv("GC_CREDENTIALS_PATH", "keys/credentials.json")

LINE_DEVS_ID: list[str] = os.getenv("LINE_DEVS_ID", "").split(",")

PORT: int = int(os.getenv("PORT", "11111"))

LINE_TOKEN: str = os.getenv("LINE_TOKEN", "")

CHANNEL_SECRET: str = os.getenv("CHANNEL_SECRET", "")
