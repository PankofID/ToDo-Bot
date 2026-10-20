from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services.notification import process_due_reminders


scheduler = AsyncIOScheduler()


def start_scheduler(bot: Bot, pool):
    scheduler.add_job(
        process_due_reminders,
        trigger="interval",
        seconds=30,
        args=[bot, pool],
        id="process_due_reminders",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()