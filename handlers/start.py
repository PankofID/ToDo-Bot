from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


start_router = Router()

# Меню кнопок в команде "Старт"
def get_main_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать задачу"), KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="🔔 Напоминания"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Команда "Старт"
@start_router.message(Command("start"))
@start_router.message(F.text.lower() == "старт")
async def start(message: Message):
    await message.answer("Привет!", reply_markup=get_main_reply_keyboard())