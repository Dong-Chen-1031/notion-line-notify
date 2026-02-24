import asyncio

from api.classroom import send_announcement
from api.notion import get_upcoming_tasks
from linex import Client, TextMessageContext, logger
from settings import GC_TOKEN_PATH, GROUP_ID, LINE_DEVS_ID

client = Client(
    "3e0ee60f2b434fd37ae6791b1e62c2c5",
    "6RwBxvXE63Cgcq4FHOR2SamjX/UQEblQKFCRC3vcgbS2hHcP/JQOAQG1Ip1SOYhDhm9zEGwqbOGxPyZxqn9Ygoc66i4+qsc3vTtPTLgHq7w3tR1pq4ZkP46G4opuUpUFzR7LoPKfeo40KhX3vgre2QdB04t89/1O/w1cDnyilFU=",
)


@client.event
async def on_ready():
    logger.log(f"Logged in as {client.user.name}")


@client.command(name="send")
async def send(ctx: TextMessageContext):
    author = await ctx.author()
    if author.id != LINE_DEVS_ID:
        return
    await send_message()
    await ctx.reply("已發送作業訊息！")


@client.command(name="login")
async def login(ctx: TextMessageContext): ...


@client.event
async def on_text(ctx: TextMessageContext):
    if ctx.text in ["send", "login"]:
        return
    if ctx.source_type == "user":
        await ctx.reply("有讀狀態訊息的同學都知道，不要私訊我，要私訊請找另一個 Dong。")


async def send_message():
    msg = ""
    tasks = get_upcoming_tasks()
    if tasks:
        msg += "以下是未來的作業：\n"
        for task in tasks:
            msg += f"- {task.subject} - {task.name}  |  截止日期：{task.deadline.strftime('%Y-%m-%d')}\n"
    else:
        msg += "\n\n目前沒有未來的作業。"
    await client.send_message(
        GROUP_ID,
        msg,
    )

    await asyncio.to_thread(lambda: send_announcement(msg, token_path=GC_TOKEN_PATH))


client.run(port=11111)
