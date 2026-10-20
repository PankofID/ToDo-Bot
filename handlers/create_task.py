from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from datetime import datetime

from handlers.start import get_main_reply_keyboard
from database import db_create_task
from services.notification import create_task_reminder

create_task_router = Router()


# Отмена создания задачи
def get_cancel_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отменить")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_skip_cancel_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить")],
            [KeyboardButton(text="Отменить")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_priority_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
            InlineKeyboardButton(text="Низкий", callback_data="priority:low"),
            InlineKeyboardButton(text="Средний", callback_data="priority:medium"),
            InlineKeyboardButton(text="Высокий", callback_data="priority:high")
            ]
        ]
    )
    return keyboard

def get_skip_date_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить (сегодня)", callback_data="deadline:skip_date")]
        ]
    )

def get_skip_time_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить (00:00)", callback_data="deadline:skip_time")]
        ]
    )

# Собирает datetime из строк ДД-ММ-ГГГГ и ЧЧ:ММ.
def parse_deadline(date_str: str, time_str: str) -> datetime:
    return datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")

def get_return_main_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Вернутся в главное меню")],
            [KeyboardButton(text="Мои задачи")]
        ],
        resize_keyboard=True
    )
    return keyboard


# Форма задачи
class TaskForm(StatesGroup):
    title = State()
    description = State()
    priority = State()
    deadline_date = State()
    deadline_time = State()


# Создание задачи
@create_task_router.message(Command("create_task"))
@create_task_router.message(F.text.lower() == "создать задачу")
@create_task_router.message(F.text.lower() == "➕ создать задачу")
async def create_task(message: Message, state: FSMContext):
    await message.answer("Название: ", reply_markup=get_cancel_reply_keyboard())
    await state.set_state(TaskForm.title)

# В случае отмены возвращаем в главное меню
@create_task_router.message(StateFilter("*"), F.text.lower() == "отменить")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Возврат в главное меню", reply_markup=get_main_reply_keyboard())

@create_task_router.message(TaskForm.title, F.text)
async def process_name(message: Message, state: FSMContext):
    if len(message.text) < 3:
        await message.answer("Слишком маленькое название")
        return
    if len(message.text) > 100:
        await message.answer("Слишком длинное название")
        return

    await state.update_data(title=message.text)

    await message.answer("Описание: ", reply_markup=get_skip_cancel_reply_keyboard())
    await state.set_state(TaskForm.description)

@create_task_router.message(TaskForm.description, F.text)
async def process_description(message: Message, state: FSMContext):
    if len(message.text) > 1000:
        await message.answer("Слишком длинное описание")
        return
    if message.text.lower() == "пропустить":
        await state.update_data(description="-")
    else:
        await state.update_data(description=message.text)

    await message.answer("Приоритет: ", reply_markup=get_priority_inline_keyboard())
    await message.answer("Выберите один из трех вариантов", reply_markup=get_cancel_reply_keyboard())
    await state.set_state(TaskForm.priority)

@create_task_router.callback_query(TaskForm.priority, F.data.startswith("priority:"))
async def process_priority_callback(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":")[1]

    priority_map = {
        "low":    "Низкий",
        "medium": "Средний",
        "high":   "Высокий",
    }
    await state.update_data(priority=priority_map[value])

    await callback.answer(f"Выбрано: {priority_map[value]}")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.edit_text(f"Приоритет: {priority_map[value]}")

    sent = await callback.message.answer("Введите дату deadline в формате ДД-ММ-ГГГГ", reply_markup=get_skip_date_inline_keyboard())
    await state.update_data(date_keyboard_message_id=sent.message_id)

    await callback.message.answer("Например: 25-12-2026", reply_markup=get_cancel_reply_keyboard())
    await state.set_state(TaskForm.deadline_date)

# Время
@create_task_router.message(TaskForm.deadline_date, F.text)
async def process_deadline_date(message: Message, state: FSMContext):
    text = message.text.strip()

    if len(text) != 10 or text[2] != "-" or text[5] != "-":
        await message.answer("Формат строго ДД-ММ-ГГГГ, например 25-12-2026")
        return

    try:
        date = datetime.strptime(text, "%d-%m-%Y").date()
    except ValueError:
        await message.answer("Неверная дата. Введите как ДД-ММ-ГГГГ, например 25-12-2026")
        return

    data = await state.get_data()
    keyboard_id = data.get("date_keyboard_message_id")
    if keyboard_id:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=keyboard_id,
                reply_markup=None
            )
        except Exception:
            pass

    await state.update_data(deadline_date=date.strftime("%d-%m-%Y"))

    sent = await message.answer("Введите время в формате ЧЧ:ММ", reply_markup=get_skip_time_inline_keyboard())
    await state.update_data(time_keyboard_message_id=sent.message_id)
    await message.answer("Например: 09:05", reply_markup=get_cancel_reply_keyboard())
    await state.set_state(TaskForm.deadline_time)

@create_task_router.callback_query(TaskForm.deadline_date, F.data == "deadline:skip_date")
async def skip_deadline_date(callback: CallbackQuery, state: FSMContext):
    today = datetime.now().strftime("%d-%m-%Y")
    await state.update_data(deadline_date=today)

    await callback.answer("Дата: сегодня")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.edit_text(f"Дата: {today}")

    sent = await callback.message.answer("Введите время в формате ЧЧ:ММ", reply_markup=get_skip_time_inline_keyboard())
    await state.update_data(time_keyboard_message_id=sent.message_id)
    await callback.message.answer("Например: 09:05", reply_markup=get_cancel_reply_keyboard())
    await state.set_state(TaskForm.deadline_time)

@create_task_router.message(TaskForm.deadline_time, F.text)
async def process_deadline_time(message: Message, state: FSMContext, pool):
    text = message.text.strip()

    if len(text) != 5 or text[2] != ":":
        await message.answer("Формат строго ЧЧ:ММ, например 09:05")
        return

    try:
        time = datetime.strptime(text, "%H:%M").time()
    except ValueError:
        await message.answer("Неверное время. Введите как ЧЧ:ММ, например 09:05")
        return

    data = await state.get_data()
    date_str = data.get("deadline_date")

    try:
        deadline_dt = parse_deadline(date_str, time.strftime("%H:%M"))
    except ValueError:
        await message.answer("Не удалось собрать дату. Введите время заново.")
        return

    if deadline_dt < datetime.now():
        await message.answer(
            "Дедлайн уже в прошлом. Введите время позже текущего\n"
            f"(сейчас {datetime.now().strftime('%H:%M')}, дата {date_str})."
        )
        return

    keyboard_id = data.get("time_keyboard_message_id")
    if keyboard_id:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=keyboard_id,
                reply_markup=None
            )
        except Exception:
            pass

    await state.update_data(deadline_time=time.strftime("%H:%M"))
    await finalize_task(message, state, pool)

@create_task_router.callback_query(TaskForm.deadline_time, F.data == "deadline:skip_time")
async def skip_deadline_time(callback: CallbackQuery, state: FSMContext, pool):
    data = await state.get_data()
    date_str = data.get("deadline_date")

    deadline_dt = parse_deadline(date_str, "00:00")
    if deadline_dt < datetime.now():
        await callback.answer(
            "00:00 этой даты уже в прошлом. Введите время вручную.",
            show_alert=True
        )
        return

    await state.update_data(deadline_time="00:00")
    await callback.answer("Время: 00:00")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.edit_text("⏰ Время: 00:00")
    await finalize_task(callback.message, state, pool)

@create_task_router.message(F.text.lower() == "вернутся в главное меню")
async def return_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=get_main_reply_keyboard())

async def finalize_task(message: Message, state: FSMContext, pool):
    data = await state.get_data()

    user_id = message.from_user.id
    title = data["title"]
    description = data["description"]
    priority = data["priority"]

    deadline = datetime.strptime(
        f'{data["deadline_date"]} {data["deadline_time"]}',
        "%d-%m-%Y %H:%M",
    )

    task_id = await db_create_task(pool, user_id, title, description, priority, deadline)

    await create_task_reminder(pool=pool,task_id=task_id,deadline=deadline,)

    text = (
        "✅ Задача создана!\n\n"
        f"📌 Название: {title}\n"
        f"📝 Описание: {description}\n"
        f"⚡ Приоритет: {priority}\n"
        f"⏰ Deadline: {deadline:%d-%m-%Y %H:%M}"
    )

    await message.answer(text,reply_markup=get_return_main_reply_keyboard())

    await state.clear()