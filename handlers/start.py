from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


start_router = Router()

# Меню кнопок в команде "Старт"
def get_main_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="➕ Создать задачу"), KeyboardButton(text="🔔 Напоминания")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="❗ Информация")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Команда "Старт"
@start_router.message(Command("start"))
@start_router.message(F.text.lower() == "старт")
async def start(message: Message):
    user_name = message.from_user.first_name or "друг"

    await message.answer(
        f"👋 Привет, <b>{user_name}</b>!\n\n"
        "<b>Todo-бот</b> - это Telegram-бот для управления задачами: "
        "помогает создавать, хранить и просматривать списки дел, ставить напоминания и отслеживать статистику, "
        "чтобы ничего не забывать и всё успевать.\n"
        "• <b>📋 Мои задачи</b> - просмотр всех твоих дел\n"
        "• <b>➕ Создать задачу</b> - добавление новой задачи\n"
        "• <b>🔔 Напоминания</b> - уведомления в нужное время\n"
        "• <b>📊 Статистика</b> - твой прогресс и продуктивность\n"
        "• <b>⚙️ Настройки</b> - персонализация под тебя\n"
        "• <b>❗ Информация</b> - информация о боте и разработчике\n\n"
        "Выбери действие на клавиатуре ниже или нажми <b>❓ Помощь</b>, если что-то непонятно.",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="html"
    )