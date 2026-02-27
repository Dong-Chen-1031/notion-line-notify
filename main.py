from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from objprint import op

from api.notion import get_upcoming_tasks
from linex import Client, JoinContext, TextMessageContext, logger
from settings import CHANNEL_SECRET, GROUP_ID, LINE_DEVS_ID, LINE_TOKEN, PORT
from utils.message import create_line_message

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
async def on_join(ctx: JoinContext):
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
