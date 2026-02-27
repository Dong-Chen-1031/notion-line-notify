from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from objprint import op

from api.notion import Task, get_upcoming_tasks
from linex import Client, TextMessageContext, logger
from linex.models.messages import Flex
from settings import CHANNEL_SECRET, GROUP_ID, LINE_DEVS_ID, LINE_TOKEN, PORT

client = Client(CHANNEL_SECRET, LINE_TOKEN)

scheduler = AsyncIOScheduler()


@client.event
async def on_ready():
    logger.log(f"Logged in as {client.user.display_name}")
    scheduler.start()


@client.command(name="send")
async def send(ctx: TextMessageContext):
    author = await ctx.fetch_user()
    if author.id not in LINE_DEVS_ID:
        return
    await send_message()
    await ctx.reply("已發送作業訊息到群組！")


@client.event
async def on_join(ctx: TextMessageContext):
    op(await ctx.fetch_group())


@client.command(name="test")
async def test(ctx: TextMessageContext):
    if ctx.source_type != "user":
        return await ctx.mark_as_read()

    author = ctx.source_as_user()
    if author.id not in LINE_DEVS_ID:
        return

    await ctx.mark_as_read()
    tasks = await get_upcoming_tasks()
    await ctx.reply(create_line_message(tasks))


@client.command(name="info")
async def info(ctx: TextMessageContext):
    author = ctx.source_as_group()
    # if author.id not in LINE_DEVS_ID:
    #     return

    await ctx.mark_as_read()
    await ctx.reply(f"群組 ID: {author.id}")


@client.event
async def on_text(ctx: TextMessageContext):
    if await client.process_commands(ctx):
        return
    if ctx.source_type == "user":
        await ctx.mark_as_read()
        await ctx.reply("有讀狀態訊息的同學都知道，不要私訊我，要私訊請找另一個 Dong。")


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
    date = f"{now.month}/{now.day} ({weekday_to_chinese[now.weekday()]})"
    tasks_by_subject: dict[str, list[Task]] = {}
    for task in tasks:
        tasks_by_subject.setdefault(task.subject, []).append(task)

    tasks_str_by_subject: dict[str, str] = {}

    for subject, tasks in tasks_by_subject.items():
        tasks_str = "\n".join(
            [
                f"{str(i + 1) + '. ' if len(tasks) != 1 else ''}{smarter_format_date(task.deadline)} {task.name}"
                for i, task in enumerate(tasks)
            ]
        )
        tasks_str_by_subject[subject] = tasks_str.strip()

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
                                        "text": f"星期{weekday_to_chinese[now.weekday()]}",
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
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": subject,
                                        "color": "#aaaaaa",
                                        "size": "sm",
                                        "flex": 2,
                                    },
                                    {
                                        "type": "text",
                                        "text": tasks_str,
                                        "wrap": True,
                                        "color": "#666666",
                                        "size": "sm",
                                        "flex": 6,
                                    },
                                ],
                            }
                            for subject, tasks_str in tasks_str_by_subject.items()
                        ],
                    },
                ],
            },
            "styles": {"header": {"separator": False}},
        },
        alt_text=f"{date} 的作業\n"
        + "\n".join(
            [
                f"{subject}:\n{tasks_str}"
                for subject, tasks_str in tasks_str_by_subject.items()
            ]
        ),
    )
    return message


async def send_message():
    tasks = await get_upcoming_tasks()

    await client.send_message(
        GROUP_ID,
        create_line_message(tasks),
    )


async def scheduled_send_message():
    if datetime.now(ZoneInfo("Asia/Taipei")).weekday() == 5:
        return
    await send_message()


# fc4e42

scheduler.add_job(
    scheduled_send_message,
    "cron",
    hour=17,
    minute=00,
    timezone=ZoneInfo("Asia/Taipei"),
)


client.run(port=PORT)
