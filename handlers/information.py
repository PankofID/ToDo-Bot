from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message


info_router = Router()

@info_router.message(Command("info"))
@info_router.message(F.text.lower() == "информация")
@info_router.message(F.text.lower() == "❗ информация")
async def info(message: Message):
    await message.answer(
        "ℹ️ <b>О боте</b>\n\n"
        "<b>Todo-бот</b> - это Telegram-бот для управления задачами: "
        "помогает создавать, хранить и просматривать списки дел, ставить напоминания и отслеживать статистику, "
        "чтобы ничего не забывать и всё успевать.\n"
        "👨‍💻 <b>Автор:</b> PankofID\n"
        "💬 <b>Telegram:</b> @PankofID\n"
        "🐙 <b>GitHub:</b> github.com/PankofID\n"
        "📦 <b>Репозиторий бота:</b> github.com/PankofID/ToDo-Bot\n"
        "📄 <b>Лицензия:</b> MIT License",
        parse_mode="html",
        disable_web_page_preview=True)