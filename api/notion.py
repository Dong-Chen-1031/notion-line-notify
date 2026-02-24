from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from notion_client import Client as NotionClient

from settings import NOTION_TOKEN

notion = NotionClient(auth=NOTION_TOKEN)


class CanGetNone:
    def __getitem__(self, key: Any) -> Any:
        return self

    def __bool__(self) -> Literal[False]:
        return False


class SaveDict(dict):
    def __getitem__(self, key: Any) -> Any:
        _ = super().get(key)
        if isinstance(_, dict):
            return SaveDict(_)
        if _ is None:
            return CanGetNone()
        return _


class Task:
    name: str
    subject: str
    deadline: datetime

    def __init__(self, data: dict):
        data = SaveDict(data)
        self.name = data["properties"]["作業名稱"]["title"][0]["plain_text"] or "無名稱"
        self.subject = data["properties"]["科目"]["select"]["name"] or "無科目"
        self.deadline = datetime.fromisoformat(
            data["properties"]["截止日期"]["date"]["start"]
        )


def get_upcoming_tasks() -> list[Task]:
    """取得所有未來的作業

    Returns:
        list[Task]: 未來的作業列表
    """
    tasks: dict[str, Any | list[dict]] = notion.data_sources.query(
        "262be96b-9601-8014-bb40-000b34f82910",
        filter={
            "property": "截止日期",
            "date": {
                "on_or_after": datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()
            },
        },
        sorts=[
            {"property": "截止日期", "direction": "ascending"},
        ],
    )  # type: ignore

    return [Task(result) for result in tasks["results"]]


{
    "archived": False,
    "cover": None,
    "created_by": {"id": "c5db06ff-a234-47fe-8d58-35f785cef931", "object": "user"},
    "created_time": "2026-02-24T00:43:00.000Z",
    "icon": {
        "external": {"url": "https://www.notion.so/icons/school_gray.svg"},
        "type": "external",
    },
    "id": "311be96b-9601-807a-9b81-e2f1a820aef1",
    "in_trash": False,
    "is_locked": False,
    "last_edited_by": {"id": "c5db06ff-a234-47fe-8d58-35f785cef931", "object": "user"},
    "last_edited_time": "2026-02-24T00:44:00.000Z",
    "object": "page",
    "parent": {
        "data_source_id": "262be96b-9601-8014-bb40-000b34f82910",
        "database_id": "262be96b-9601-806b-b3ff-e7708c712e2c",
        "type": "data_source_id",
    },
    "properties": {
        "作業名稱": {
            "id": "title",
            "title": [
                {
                    "annotations": {
                        "bold": False,
                        "code": False,
                        "color": "default",
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                    },
                    "href": None,
                    "plain_text": "實驗預報",
                    "text": {"content": "實驗預報", "link": None},
                    "type": "text",
                }
            ],
            "type": "title",
        },
        "優先級": {"id": "y%5ElO", "select": None, "type": "select"},
        "截止日期": {
            "date": {"end": None, "start": "2026-03-03", "time_zone": None},
            "id": "AJUd",
            "type": "date",
        },
        "狀態": {
            "id": "xxDB",
            "status": {"color": "gray", "id": "CNXC", "name": "未開始"},
            "type": "status",
        },
        "科目": {
            "id": "TYOm",
            "select": {
                "color": "brown",
                "id": "fb451ca5-97d2-4ac8-9d79-43f70a90ef7a",
                "name": "生化探究",
            },
            "type": "select",
        },
        "網址": {"id": "%5DxL~", "type": "url", "url": None},
        "難度": {"id": "rGF%5D", "select": None, "type": "select"},
        "預計完成日期": {"date": None, "id": "%3ApfQ", "type": "date"},
    },
    "public_url": None,
    "url": "https://www.notion.so/311be96b9601807a9b81e2f1a820aef1",
}  # type: ignore
