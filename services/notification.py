from datetime import datetime, timedelta
import logging

from aiogram import Bot

from database import get_reminders, set_reminder_status


logger = logging.getLogger(__name__)


REMINDER_OFFSETS = {
    "week": timedelta(days=7),
    "day": timedelta(days=1),
    "deadline": timedelta(days=0),
}

REMINDER_MESSAGES = {
    "week": "До deadline осталась неделя!",
    "day": "До deadline остался один день!",
    "deadline": "Наступил deadline!",
}


async def create_task_reminder(pool, task_id: int, deadline: datetime):
    now = datetime.now()

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM task_reminders
                WHERE task_id = $1
                  AND status = 'pending'
                """,
                task_id,
            )

            for reminder_type, offset in REMINDER_OFFSETS.items():
                scheduled_at = deadline - offset

                if scheduled_at <= now:
                    continue

                await conn.execute(
                    """
                    INSERT INTO task_reminders (
                        task_id,
                        reminder_type,
                        deadline_snapshot,
                        scheduled_at
                    )
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (
                        task_id,
                        deadline_snapshot,
                        reminder_type
                    )
                    DO NOTHING
                    """,
                    task_id,
                    reminder_type,
                    deadline,
                    scheduled_at,
                )


async def process_due_reminders(bot: Bot, pool):
    reminders = await get_reminders(pool)

    for reminder in reminders:
        reminder_id = reminder["reminder_id"]

        if not reminder["notification_enabled"]:
            await set_reminder_status(pool, reminder_id, "skipped")
            continue

        if reminder["task_status"] == "completed":
            await set_reminder_status(pool, reminder_id, "skipped")
            continue

        if reminder["deadline"] != reminder["deadline_snapshot"]:
            await set_reminder_status(pool, reminder_id, "skipped")
            continue

        message = REMINDER_MESSAGES[reminder["reminder_type"]]

        try:
            await bot.send_message(
                chat_id=reminder["user_id"],
                text=(
                    f"{message}\n\n"
                    f"Задача: {reminder['title']}"
                ),
            )
        except Exception:
            logger.exception("Не удалось отправить напоминание %s",reminder_id,)
            continue

        await set_reminder_status(pool, reminder_id, "sent")