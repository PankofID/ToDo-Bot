from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message


help_router = Router()

@help_router.message(Command("help"))
@help_router.message(F.text.lower() == "помощь")
@help_router.message(F.text.lower() == "❓ помощь")
async def help(message: Message):
    await message.answer(
        "/start - Главное меню\n"
        "/create_task - Создать задачу\n"
        "/my_tasks - Мои задачи\n"
        "/notification - Уведомления\n"
        "/statistics - Статистика\n"
        "/settings - Настройки\n"
        "/help - Помощь"
                         )