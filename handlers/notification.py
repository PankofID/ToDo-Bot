from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_notifications_enabled, set_notifications_enabled


notification_router = Router()

def get_notification_inline(is_enabled: bool) -> InlineKeyboardMarkup:
    if is_enabled:
        keyboard = [[InlineKeyboardButton(text="🔕 Отписаться от уведомлений", callback_data="notif:off")]]
    else:
        keyboard = [[InlineKeyboardButton(text="🔔 Подписаться на уведомления", callback_data="notif:on")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@notification_router.message(Command("notification"))
@notification_router.message(F.text.lower() == "напоминания")
@notification_router.message(F.text.lower() == "🔔 напоминания")
async def notification(message: Message, pool):
    enabled = await get_notifications_enabled(pool, message.from_user.id)
    status = "включены" if enabled else "выключены"

    await message.answer(
        f"Уведомления сейчас {status}.\n"
        "Если включены — напомним за неделю, за сутки и в момент deadline задачи.",
        reply_markup=get_notification_inline(enabled),
    )

@notification_router.callback_query(F.data.in_({"notif:on", "notif:off"}))
async def toggle_notifications(callback: CallbackQuery, pool):
    enabled = callback.data == "notif:on"
    await set_notifications_enabled(pool, callback.from_user.id, enabled)

    text = (
        "✅ Уведомления включены.\n Напомним за неделю, за сутки и в момент deadline."
        if enabled else
        "🔕 Уведомления выключены.\n Если включить — напомним за неделю, за сутки и в момент deadline задачи."
    )

    await callback.message.edit_text(text, reply_markup=get_notification_inline(enabled))
    await callback.answer()

