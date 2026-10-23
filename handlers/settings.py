from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_default_sort, set_default_sort


settings_router = Router()

async def get_settings_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Часовой пояс (В РАЗРАБОТКЕ)", callback_data="settings:timezone")], [InlineKeyboardButton(text="Формат даты и времени (В РАЗРАБОТКЕ)", callback_data="settings:datetime_format")],
            [InlineKeyboardButton(text="Сортировка задач", callback_data="settings:sort")],
        ]
    )
    return keyboard

async def get_setting_sort_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="По названию", callback_data="sort:title")],
            [InlineKeyboardButton(text="По дате создания (от нового к старому)", callback_data="sort:created:new")], [InlineKeyboardButton(text="По дате создания (от старого к новому)", callback_data="sort:created:old")],
            [InlineKeyboardButton(text="По deadline", callback_data="sort:deadline")],
            [InlineKeyboardButton(text="По приоритету", callback_data="sort:priority")],
            [InlineKeyboardButton(text="Назад", callback_data="settings:back")],

        ]
    )
    return keyboard


@settings_router.message(Command("settings"))
@settings_router.message(F.text.lower() == "⚙️ настройки")
@settings_router.message(F.text.lower() == "настройки")
async def settings(message: Message):
    await message.answer("Настройки", reply_markup=await get_settings_inline_keyboard())


# Сортировка
@settings_router.callback_query(F.data == "settings:sort")
async def setting_sort(callback_query: CallbackQuery, pool):
    default_sort = await get_default_sort(pool, callback_query.from_user.id)
    sort_value = {
        "title": "По названию",
        "created_desc": "от новых к старым",
        "created_asc": "от старых к новым",
        "deadline": "по deadline",
        "priority": "по приоритету"
    }
    current = sort_value.get(default_sort, "не задано")
    await callback_query.message.edit_text(f"Выберите способ сортировки задач\n\nСейчас: {current}", reply_markup=await get_setting_sort_inline_keyboard())
    await callback_query.answer()

@settings_router.callback_query(F.data == "sort:title")
async def setting_sort_title(callback_query: CallbackQuery, pool):
    await set_default_sort(pool, callback_query.from_user.id, "title")

    await callback_query.message.edit_text("Сортировка задач изменена: по названию.")
    await callback_query.answer()

@settings_router.callback_query(F.data == "sort:created:new")
async def setting_sort_created_desc(callback_query: CallbackQuery, pool):
    await set_default_sort(pool, callback_query.from_user.id, "created_desc")

    await callback_query.message.edit_text("Сортировка задач изменена: от новых к старым.")
    await callback_query.answer()

@settings_router.callback_query(F.data == "sort:created:old")
async def setting_sort_created_asc(callback_query: CallbackQuery, pool):
    await set_default_sort(pool, callback_query.from_user.id, "created_asc")

    await callback_query.message.edit_text("Сортировка задач изменена: от старых к новым.")
    await callback_query.answer()

@settings_router.callback_query(F.data == "sort:deadline")
async def setting_sort_deadline(callback_query: CallbackQuery, pool):
    await set_default_sort(pool, callback_query.from_user.id, "deadline")

    await callback_query.message.edit_text("Сортировка задач изменена: по deadline.")
    await callback_query.answer()

@settings_router.callback_query(F.data == "sort:priority")
async def setting_sort_priority(callback_query: CallbackQuery, pool):
    await set_default_sort(pool, callback_query.from_user.id, "priority")

    await callback_query.message.edit_text("Сортировка задач изменена: по приоритету.")
    await callback_query.answer()

@settings_router.callback_query(F.data == "settings:back")
async def setting_back(callback_query: CallbackQuery):
    await callback_query.message.edit_text("Настройки", reply_markup=await get_settings_inline_keyboard())
    await callback_query.answer()