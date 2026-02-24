import os

from dotenv import load_dotenv

load_dotenv()

GROUP_ID = os.getenv("GROUP_ID", "")

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")

GC_TOKEN_PATH = os.getenv("GC_TOKEN_PATH", "keys/token.json")

GC_CREDENTIALS_PATH = os.getenv("GC_CREDENTIALS_PATH", "keys/credentials.json")

LINE_DEVS_ID = os.getenv("LINE_DEVS_ID", "")
