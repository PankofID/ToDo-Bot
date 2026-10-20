import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from os import getenv

from handlers.start import start_router
from handlers.create_task import create_task_router
from handlers.my_tasks import my_tasks_router
from handlers.notification import notification_router
from handlers.help import help_router

from database import create_pool
from scheduler import scheduler, start_scheduler

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher()

dp.include_router(start_router)
dp.include_router(create_task_router)
dp.include_router(my_tasks_router)
dp.include_router(notification_router)
dp.include_router(help_router)


async def main():
    bot = Bot(token=TOKEN)
    pool = await create_pool()

    print("Start...")

    try:
        start_scheduler(bot, pool)
        await dp.start_polling(bot, pool=pool)
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())