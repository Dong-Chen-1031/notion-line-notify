#!/usr/bin/env python3

import asyncio

import typer

app = typer.Typer(suggest_commands=True)


@app.command()
def todo():
    """Get Todo List From Notion"""
    from api.notion import get_upcoming_tasks

    typer.echo(asyncio.run(get_upcoming_tasks()))


@app.command()
def test():
    """Get Todo List From Notion"""
    from api.notion import get_upcoming_tasks
    from utils.message import create_line_message

    async def get_msg():
        tasks = await get_upcoming_tasks()
        msg = create_line_message(tasks).to_json()
        return msg

    typer.echo(asyncio.run(get_msg()))


if __name__ == "__main__":
    app()
