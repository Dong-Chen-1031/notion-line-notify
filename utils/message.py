from datetime import datetime
from zoneinfo import ZoneInfo

from api.notion import Task
from linex.models.messages import Flex

weekday_to_chinese = ["一", "二", "三", "四", "五", "六", "日"]


def smarter_format_date(date: datetime) -> str:
    now = datetime.now(ZoneInfo("Asia/Taipei")).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    timedelta_ = date - now
    if timedelta_.days == 0:
        return "今天"
    elif timedelta_.days == 1:
        return "明天"
    elif timedelta_.days == 2:
        return "後天"
    else:
        week_delta = now.isocalendar().week - date.isocalendar().week
        if week_delta == 0:
            return f"本週{weekday_to_chinese[date.weekday()]}"
        elif week_delta == -1:
            return f"下週{weekday_to_chinese[date.weekday()]}"
        else:
            return date.strftime("%m/%d") + f" ({weekday_to_chinese[date.weekday()]})"


def create_line_message(tasks: list[Task]) -> Flex:
    now = datetime.now(ZoneInfo("Asia/Taipei"))
    # date = f"{now.month}/{now.day} ({weekday_to_chinese[now.weekday()]})"
    tasks_by_subject: dict[str, list[Task]] = {}
    for task in tasks:
        tasks_by_subject.setdefault(task.subject, []).append(task)

    tasks_str_by_subject: dict[str, list[str]] = {}

    for subject, subject_tasks in tasks_by_subject.items():
        tasks_str = [
            f"{str(i + 1) + '. ' if len(subject_tasks) != 1 else ''}{smarter_format_date(task.deadline)} {task.name}"
            for i, task in enumerate(subject_tasks)
        ]

        tasks_str_by_subject[subject] = tasks_str

    # print(tasks_str_by_subject)
    all_homework = []
    for subject, tasks_str in tasks_str_by_subject.items():
        for i, text in enumerate(tasks_str):
            all_homework.append(
                {
                    "type": "box",
                    "layout": "baseline",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": subject if i == 0 else " ",
                            "color": "#aaaaaa",
                            "size": "sm",
                            "flex": 2,
                        },
                        {
                            "type": "text",
                            "text": text,
                            "wrap": True,
                            "color": "#fc4e42" if "明天" in text else "#666666",
                            "size": "sm",
                            "flex": 6,
                        },
                    ],
                }
            )

    message = Flex(
        {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": f"週{weekday_to_chinese[now.weekday()]}",
                                        "color": "#fc4e42",
                                        "align": "center",
                                        "size": "xs",
                                        "offsetTop": "4px",
                                    },
                                    {
                                        "type": "text",
                                        "text": f"{now.day}",
                                        "align": "center",
                                        "size": "xxl",
                                    },
                                ],
                                "cornerRadius": "md",
                                "alignItems": "center",
                                "backgroundColor": "#f1f1f1",
                                "justifyContent": "center",
                                "width": "60px",
                                "height": "60px",
                            },
                            {
                                "type": "text",
                                "text": "今日提醒事項",
                                "weight": "bold",
                                "size": "xl",
                            },
                        ],
                        "justifyContent": "flex-start",
                        "alignItems": "center",
                        "spacing": "20px",
                        "paddingBottom": "12px",
                    },
                    {"type": "separator"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": all_homework,
                    },
                ],
            },
            "styles": {"header": {"separator": False}},
        },
        alt_text=create_alt_text(tasks),
    )
    return message


def create_alt_text(tasks: list[Task]) -> str:
    if len(tasks) == 0:
        return "今天沒有任何事做，可以內卷了！"

    task = tasks[0]
    return f"{task.subject}：「{task.name}」" + (
        f"，還有其他 {len(tasks) - 1} 項" if len(tasks) > 1 else ""
    )
