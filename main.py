from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from objprint import op

from api.notion import get_upcoming_tasks
from linex import Client, Image, JoinContext, TextMessageContext, logger
from settings import (
    CDN_BASE,
    CHANNEL_SECRET,
    DEV_MODE,
    GROUP_ID,
    LINE_DEVS_ID,
    LINE_TOKEN,
    PORT,
)
from utils.message import create_line_message

client = Client(CHANNEL_SECRET, LINE_TOKEN)

scheduler = AsyncIOScheduler()


@client.event
async def on_ready():
    logger.log(f"Logged in as {client.user.display_name}")
    scheduler.start()


@client.event
async def on_join(ctx: JoinContext):
    op(await ctx.fetch_group())


@client.command(name="send")
async def send(ctx: TextMessageContext):
    author = await ctx.fetch_user()
    if author.id not in LINE_DEVS_ID:
        return
    await send_message()
    await ctx.reply("已發送作業訊息到群組！")


@client.command(name="課表")
async def classtable(ctx: TextMessageContext):
    await ctx.reply(Image(original_content_url=CDN_BASE + "/classtable.png"))


@client.command(name="test")
async def test(ctx: TextMessageContext):
    # if ctx.source_type != "user":
    #     return await ctx.mark_as_read()

    # author = ctx.source_as_user()
    # if author.id not in LINE_DEVS_ID:
    #     return
    author = await ctx.fetch_user()
    print(author)
    if author.id not in LINE_DEVS_ID:
        print("not dev")
        return

    # await ctx.mark_as_read()
    print("fetching tasks")
    tasks = await get_upcoming_tasks()
    print("fetched tasks")
    await ctx.reply(create_line_message(tasks))
    print("sent")


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
        await ctx.reply(
            "有讀狀態訊息的同學都知道，不要私訊我，要私訊請找另一個 Dong。",
            Image(
                original_content_url=CDN_BASE + "/志仁.png",
                preview_image_url=CDN_BASE + "/志仁.jpeg",
            ),
        )


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


scheduler.add_job(
    scheduled_send_message,
    "cron",
    hour=17,
    minute=00,
    timezone=ZoneInfo("Asia/Taipei"),
)


if DEV_MODE:
    app = client.app
else:
    client.run(port=PORT)
