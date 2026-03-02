import os

from dotenv import load_dotenv

load_dotenv()

DEV_MODE: bool = os.getenv("DEV_MODE", "False").lower() in ("true", "1", "t")

if DEV_MODE:
    load_dotenv(".env.dev", override=True)

GROUP_ID: str = os.getenv("GROUP_ID", "")

NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "")

LINE_DEVS_ID: list[str] = [
    dev_id.strip()
    for dev_id in os.getenv("LINE_DEVS_ID", "").split(",")
    if dev_id.strip()
]

PORT: int = int(os.getenv("PORT", "11111"))

LINE_TOKEN: str = os.getenv("LINE_TOKEN", "")

CHANNEL_SECRET: str = os.getenv("CHANNEL_SECRET", "")

NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "")

CDN_BASE: str = os.getenv("CDN_BASE", "")

GC_TOKEN_PATH: str = os.getenv("GC_TOKEN_PATH", "keys/token.json")

GC_TOKEN_PATH_DEV: str = os.getenv("GC_TOKEN_PATH_DEV", "keys/token.dev.json")

GC_KEYS_PATH: str = os.getenv("GC_CREDENTIALS_PATH", "keys/credentials.json")

GC_CLASS_ID: int = int(os.getenv("GC_CLASS_ID", "825932668195"))

GC_CLASS_ID_DEV: int = int(os.getenv("GC_CLASS_ID_DEV", "825932668195"))

if DEV_MODE:
    GC_TOKEN_PATH = GC_TOKEN_PATH_DEV
    GC_CLASS_ID = GC_CLASS_ID_DEV
