from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from html import escape
from typing import Optional
from datetime import datetime
import re

from database import get_tasks, get_task, db_delete_task, db_edit_status, db_edit_task
from handlers.start import get_main_reply_keyboard
from handlers.create_task import get_priority_inline_keyboard


my_tasks_router = Router()

#Функции форматирования
def format_date(date) -> str:
    if date is None:
        return "—"
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date)
        except ValueError:
            return date
    return date.strftime('%d.%m.%Y %H:%M')
def format_text_task(task) -> str:
    text = (
        f"<b>{escape(task['title'])}</b>\n"
        f"Описание: {escape(task['description'] or '')}\n"
        f"Приоритет: {task['priority']}\n"
        f"Дедлайн: {format_date(task['deadline'])}\n"
        f"Статус: {get_status_symbol(task['status'])} {get_status_text(task['status'])}\n\n"
        f"Дата создания: {format_date(task['created_at'])}"
    )

    if task['status'] == "completed" and task['completed_at']:
        text += f"\nЗавершено: {format_date(task['completed_at'])}"

    return text

def get_status_symbol(status: str) -> str:
    return "🟡" if status == "active" else "✅"
def get_status_text(status: str) -> str:
    return "Активно" if status == "active" else "Выполнено"

# inline клавиатуры
async def get_tasks_list_inline_keyboard(pool, user_id: int) -> Optional[InlineKeyboardMarkup]:
    tasks = await get_tasks(pool, user_id)
    if not tasks:
        return None

    buttons = []

    for i, task in enumerate(tasks, start=1):
        buttons.append([
            InlineKeyboardButton(
                text = (
                    f"{get_status_symbol(task['status'])}\n"
                    f"{i}. {task['title']}"),
                callback_data=f"task:{task['id']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_task_button_inline_keyboard(pool, user_id: int, task_id: int) -> Optional[InlineKeyboardMarkup]:
    task = await get_task(pool, task_id, user_id)
    if task is None:
        return None
    next_status = "completed" if task["status"] == "active" else "active"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Редактировать", callback_data=f"edit:{task_id}"), InlineKeyboardButton(text="Удалить", callback_data=f"delete:{task_id}")],
            [InlineKeyboardButton(text=f"Изменить статус на {get_status_text(next_status)}", callback_data=f"status:{task_id}")]
    ])
    return keyboard

async def get_edit_task_button_inline_keyboard(pool, user_id: int, task_id: int) -> Optional[InlineKeyboardMarkup]:
    task = await get_task(pool, task_id, user_id)
    if task is None:
        return None

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Название", callback_data=f"edit_title:{task_id}")],
            [InlineKeyboardButton(text="Описание", callback_data=f"edit_description:{task_id}")],
            [InlineKeyboardButton(text="Приоритет", callback_data=f"edit_priority:{task_id}")],
            [InlineKeyboardButton(text="Дедлайн", callback_data=f"edit_deadline:{task_id}")]
        ]
    )
    return keyboard

def get_cancel_edit_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отменить редактирование")]
        ],
        resize_keyboard=True
    )
    return keyboard


class EditTask(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_priority = State()
    waiting_deadline_date = State()
    waiting_deadline_time = State()


@my_tasks_router.message(Command("my_tasks"))
@my_tasks_router.message(F.text.lower() == "📋 мои задачи")
@my_tasks_router.message(F.text.lower() == "мои задачи")
async def my_tasks(message: Message, pool):
    keyboard = await get_tasks_list_inline_keyboard(pool, message.from_user.id)
    if keyboard is None:
        await message.answer("У вас нет задач")
        return

    await message.answer("Мои задачи", reply_markup=keyboard)

@my_tasks_router.callback_query(F.data.startswith("task:"))
async def show_task(callback: CallbackQuery, pool):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(pool, task_id, callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    text = format_text_task(task)

    await callback.answer()

    keyboard = await get_task_button_inline_keyboard(pool, callback.from_user.id, task['id'])
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
    except TelegramBadRequest:
        pass

@my_tasks_router.callback_query(F.data.startswith("delete:"))
async def delete_task(callback: CallbackQuery, pool):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(pool, task_id, callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    await db_delete_task(pool, task_id, callback.from_user.id)
    await callback.answer("Задача удалена")

    keyboard = await get_tasks_list_inline_keyboard(pool, callback.from_user.id)
    if keyboard is None:
        await callback.message.edit_text("У вас нет задач")
    else:
        await callback.message.edit_text("Мои задачи", reply_markup=keyboard)

@my_tasks_router.callback_query(F.data.startswith("status:"))
async def edit_status(callback: CallbackQuery, pool):
    task_id = int(callback.data.split(":")[1])

    updated = await db_edit_status(pool, task_id, callback.from_user.id)
    if updated is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    task = await get_task(pool, task_id, callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    text = format_text_task(task)
    keyboard = await get_task_button_inline_keyboard(pool, callback.from_user.id, task['id'])

    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
    except TelegramBadRequest:
        pass

    await callback.answer("Статус обновлён")

# --- Редактирование задачи ---
@my_tasks_router.callback_query(F.data.startswith("edit:"))
async def edit_task(callback: CallbackQuery, pool):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(pool, task_id, callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    keyboard = await get_edit_task_button_inline_keyboard(pool, callback.from_user.id, task['id'])
    try:
        await callback.message.edit_text("Выберите раздел для изменения", parse_mode='HTML', reply_markup=keyboard)
    except TelegramBadRequest:
        pass

# В случае отмены возвращаем к списку задач
@my_tasks_router.message(F.text.lower() == "отменить редактирование")
async def cancel_edit_handler(message: Message, state: FSMContext, pool):
    if await state.get_state() is None:
        return

    await state.clear()
    await message.answer("Редактирование отменено", reply_markup=get_main_reply_keyboard())

    keyboard = await get_tasks_list_inline_keyboard(pool, message.from_user.id)
    if keyboard is None:
        await message.answer("У вас нет задач")
        return

    await message.answer("Мои задачи", reply_markup=keyboard)

# FSM
# Название
@my_tasks_router.callback_query(F.data.startswith("edit_title:"))
async def edit_title_start(callback: CallbackQuery, state: FSMContext, pool):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(pool, task_id, callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    await state.set_state(EditTask.waiting_title)
    await state.update_data(task_id=task_id, message_id=callback.message.message_id)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    await callback.message.answer(
        f"Текущее название: <b>{escape(task['title'])}</b>\n\nОтправьте новое название:",
        parse_mode="HTML",
        reply_markup=get_cancel_edit_reply_keyboard()
    )
    await callback.answer()

@my_tasks_router.message(EditTask.waiting_title, F.text)
async def edit_title_save(message: Message, state: FSMContext, pool):
    data = await state.get_data()
    await state.clear()

    new_title = message.text.strip()
    if not new_title:
        await message.answer("Название не может быть пустым")
        return

    await db_edit_task(pool, data["task_id"], message.from_user.id, "title", new_title)

    await message.answer(f"Название изменено на \"{new_title}\"", reply_markup=get_main_reply_keyboard())

    task = await get_task(pool, data["task_id"], message.from_user.id)
    if task is None:
        await message.answer("Задача не найдена")
        return

    text = format_text_task(task)
    keyboard = await get_task_button_inline_keyboard(pool, message.from_user.id, task["id"])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# Описание
@my_tasks_router.callback_query(F.data.startswith("edit_description:"))
async def edit_description_start(callback: CallbackQuery, state: FSMContext, pool):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(pool, task_id, callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    await state.set_state(EditTask.waiting_description)
    await state.update_data(task_id=task_id, message_id=callback.message.message_id)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    await callback.message.answer(
        f"Текущее описание: {task['description']}\n\nОтправьте новое описание:",
        parse_mode="HTML",
        reply_markup=get_cancel_edit_reply_keyboard()
    )
    await callback.answer()

@my_tasks_router.message(EditTask.waiting_description, F.text)
async def edit_description_save(message: Message, state: FSMContext, pool):
    data = await state.get_data()
    await state.clear()

    new_description = message.text.strip()

    await db_edit_task(pool, data["task_id"], message.from_user.id, "description", new_description)

    await message.answer(f"Описание изменено на \"{new_description}\"", reply_markup=get_main_reply_keyboard())

    task = await get_task(pool, data["task_id"], message.from_user.id)
    if task is None:
        await message.answer("Задача не найдена")
        return

    text = format_text_task(task)
    keyboard = await get_task_button_inline_keyboard(pool, message.from_user.id, task["id"])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# Приоритет
@my_tasks_router.callback_query(F.data.startswith("edit_priority:"))
async def edit_priority_start(callback: CallbackQuery, state: FSMContext, pool):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(pool, task_id, callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    await state.set_state(EditTask.waiting_priority)
    await state.update_data(task_id=task_id, message_id=callback.message.message_id)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    await callback.message.answer(f"Текущий приоритет: <b>{escape(task['priority'])}</b>", parse_mode="HTML", reply_markup=get_priority_inline_keyboard())
    await callback.message.answer("Выберите один из трех вариантов", reply_markup=get_cancel_edit_reply_keyboard())
    await callback.answer()

@my_tasks_router.callback_query(EditTask.waiting_priority, F.data.startswith("priority:"))
async def process_priority_callback(callback: CallbackQuery, state: FSMContext, pool):
    value = callback.data.split(":")[1]
    priority_map = {"low": "Низкий", "medium": "Средний", "high": "Высокий"}
    new_priority = priority_map.get(value)
    if new_priority is None:
        await callback.answer("Неизвестный приоритет", show_alert=True)
        return

    data = await state.get_data()
    await state.clear()

    await db_edit_task(pool, data["task_id"], callback.from_user.id, "priority", new_priority)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    await callback.message.answer(f"Приоритет изменён на \"{new_priority}\"", reply_markup=get_main_reply_keyboard())

    task = await get_task(pool, data["task_id"], callback.from_user.id)
    if task is None:
        await callback.message.answer("Задача не найдена")
        return

    text = format_text_task(task)
    keyboard = await get_task_button_inline_keyboard(pool, callback.from_user.id, task["id"])
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# Deadline
@my_tasks_router.callback_query(F.data.startswith("edit_deadline:"))
async def edit_deadline_start(callback: CallbackQuery, state: FSMContext, pool):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(pool, task_id, callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    await state.set_state(EditTask.waiting_deadline_date)
    await state.update_data(task_id=task_id, message_id=callback.message.message_id)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    await callback.message.answer(
        f"Текущий deadline: {format_date(task['deadline'])}\n\nОтправьте новую дату в формате строго ДД-ММ-ГГГГ:",
        parse_mode="HTML",
        reply_markup=get_cancel_edit_reply_keyboard()
    )
    await callback.answer()

@my_tasks_router.message(EditTask.waiting_deadline_date, F.text)
async def edit_deadline_date(message: Message, state: FSMContext):
    new_date = message.text.strip()

    if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", new_date):
        await message.answer("Неверный формат. Введите дату строго в формате ДД-ММ-ГГГГ")
        return

    try:
        date = datetime.strptime(new_date, "%d-%m-%Y").date()
    except ValueError:
        await message.answer("Такой даты не существует. Введите дату в формате ДД-ММ-ГГГГ")
        return

    await state.update_data(deadline_date=date.isoformat())
    await state.set_state(EditTask.waiting_deadline_time)


    await message.answer(f"Отправьте время строго в формате ЧЧ:ММ", reply_markup=get_cancel_edit_reply_keyboard())

@my_tasks_router.message(EditTask.waiting_deadline_time, F.text)
async def edit_deadline_time(message: Message, state: FSMContext, pool):
    new_time = message.text.strip()

    if not re.fullmatch(r"\d{2}:\d{2}", new_time):
        await message.answer("Неверный формат. Введите время строго в формате ЧЧ:ММ")
        return

    try:
        time = datetime.strptime(new_time, "%H:%M").time()
    except ValueError:
        await message.answer("Неверное время. Введите время в формате ЧЧ:ММ")
        return

    data = await state.get_data()

    deadline_date = datetime.fromisoformat(data["deadline_date"]).date()
    deadline = datetime.combine(deadline_date, time)

    if deadline <= datetime.now():
        await state.set_state(EditTask.waiting_deadline_date)
        await state.update_data(deadline_date=None)
        await message.answer(
            "Дедлайн не может быть в прошлом.\n\n"
            "Введите дату заново в формате ДД-ММ-ГГГГ:",
            reply_markup=get_cancel_edit_reply_keyboard()
        )
        return

    await state.clear()

    await db_edit_task(pool, data["task_id"], message.from_user.id, "deadline", deadline)

    await message.answer(f"Deadline изменён на \"{format_date(deadline)}\"", reply_markup=get_main_reply_keyboard())

    task = await get_task(pool, data["task_id"], message.from_user.id)
    if task is None:
        await message.answer("Задача не найдена")
        return

    text = format_text_task(task)
    keyboard = await get_task_button_inline_keyboard(pool, message.from_user.id, task["id"])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


