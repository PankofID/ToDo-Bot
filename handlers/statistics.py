from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database import get_task_statistics

statistics_router = Router()


@statistics_router.message(Command("statistics"))
@statistics_router.message(F.text.lower() == "📊 статистика")
@statistics_router.message(F.text.lower() == "статистика")
async def statistics(message: Message, pool):
    stats = await get_task_statistics(pool, message.from_user.id)

    total = stats.get("total")
    active = stats.get("active")
    completed = stats.get("completed")
    bar_len = 20
    filled = round(bar_len * completed / total) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    text = (
        "Твоя статистика:\n"
        f"Всего задач: {total}\n\n"
        f"Активных: {active}\n"
        f"Выполнено: {completed}\n{bar} {completed / total * 100:.0f}%"
    )

    await message.answer(text)