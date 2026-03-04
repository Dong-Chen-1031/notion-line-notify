from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

WEEKDAY_TO_CHINESE = ["一", "二", "三", "四", "五", "六", "日"]


def weekday_to_chinese(dt: datetime) -> str:
    return WEEKDAY_TO_CHINESE[dt.weekday()]


def get_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Taipei")).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def smarter_format_date(date: datetime) -> str:
    now = get_now()
    delta = date - now
    if delta.days == 0:
        return "今天"
    elif delta.days == 1:
        return "明天"
    elif delta.days == 2:
        return "後天"
    else:
        start_of_this_week = now.date() - timedelta(days=now.weekday())
        start_of_target_week = date.date() - timedelta(days=date.weekday())
        week_delta = (start_of_target_week - start_of_this_week).days // 7
        if week_delta == 0:
            return f"本週{WEEKDAY_TO_CHINESE[date.weekday()]}"
        elif week_delta == 1:
            return f"下週{WEEKDAY_TO_CHINESE[date.weekday()]}"
        else:
            return date.strftime("%m/%d") + f"（{WEEKDAY_TO_CHINESE[date.weekday()]}）"
