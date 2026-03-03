import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from objprint import op

from api.classroom import send_announcement
from api.notion import get_upcoming_tasks
from linex import Client, Image, JoinContext, TextMessageContext, logger
from settings import (
    CDN_BASE,
    CHANNEL_SECRET,
    DEV_MODE,
    GC_CLASS_ID,
    GC_CLASS_ID_DEV,
    GC_TOKEN_PATH,
    GC_TOKEN_PATH_DEV,
    GROUP_ID,
    LINE_DEVS_ID,
    LINE_TOKEN,
    PORT,
)
from utils.message import create_gc_msg, create_line_message

client = Client(CHANNEL_SECRET, LINE_TOKEN)

scheduler = AsyncIOScheduler()


@client.event
async def on_ready():
    logger.log("Bot is ready!")
    logger.log(f"Logged in as {client.user.display_name}")
    scheduler.start()


@client.event
async def on_join(ctx: JoinContext):
    op(await ctx.fetch_group())


@client.command(name="send")
async def send(ctx: TextMessageContext, mode: str = "all"):
    author = await ctx.fetch_user()
    if author.id not in LINE_DEVS_ID:
        return
    mode = mode.strip().lower()
    allowed_modes = {"line", "classroom", "gc", "all"}
    if mode not in allowed_modes:
        await ctx.reply(f"無效的模式：{mode}，請使用 line、classroom、gc 或 all。")
        return
    line_flag = mode in ("line", "all")
    gc_flag = mode in ("classroom", "gc", "all")
    if not line_flag and not gc_flag:
        await ctx.reply("無效的模式，請使用 line、classroom、gc 或 all。")
        return
    await send_message(LINE=line_flag, GC=gc_flag, DEVELOP=DEV_MODE)
    await ctx.reply("已發送作業訊息到群組！")


@client.command(name="課表")
async def classtable(ctx: TextMessageContext):
    await ctx.reply(Image(original_content_url=CDN_BASE + "/classtable.png"))


@client.command(name="test")
async def test(ctx: TextMessageContext, mode: str = "all"):
    mode = mode.lower()
    author = await ctx.fetch_user()
    if author.id not in LINE_DEVS_ID:
        return

    await ctx.mark_as_read()

    tasks = await get_upcoming_tasks()
    if mode in ("line", "all"):
        await ctx.reply(create_line_message(tasks))
    if mode in ("classroom", "gc", "all"):
        await send_message(LINE=False, GC=True, DEVELOP=True)

    await ctx.reply("已發送作業訊息！")


@client.event
async def on_text(ctx: TextMessageContext):
    if await client.process_commands(ctx):
        return
    if ctx.source_type == "user":
        await ctx.mark_as_read()
        tasks = await get_upcoming_tasks()
        await ctx.reply(
            create_line_message(tasks),
            "有讀狀態訊息的同學都知道，不要私訊我，要私訊請找另一個 Dong。",
            Image(
                original_content_url=CDN_BASE + "/chih-ren.png",
                preview_image_url=CDN_BASE + "/chih-ren.jpeg",
            ),
        )


async def send_message(LINE=True, GC=True, DEVELOP=False):
    tasks = await get_upcoming_tasks()

    send_functions = []

    if LINE:
        send_functions.append(
            client.send_message(
                GROUP_ID,
                create_line_message(tasks),
            )
        )
    if GC:
        send_functions.append(
            asyncio.to_thread(
                send_announcement,
                create_gc_msg(tasks),
                GC_CLASS_ID if not DEVELOP else GC_CLASS_ID_DEV,
                GC_TOKEN_PATH if not DEVELOP else GC_TOKEN_PATH_DEV,
            )
        )
    await asyncio.gather(*send_functions)


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


if __name__ == "__main__":
    client.run(port=PORT, debug=DEV_MODE)
