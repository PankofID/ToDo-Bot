from datetime import datetime

import asyncpg

from os import getenv
from dotenv import load_dotenv

load_dotenv()


async def create_pool():
    return await asyncpg.create_pool(
        user=getenv('DB_USER'),
        password=getenv('DB_PASSWORD'),
        database=getenv('DB_DATABASE'),
        host=getenv('DB_HOST'),
        port=5432
    )

# --- Таблица tasks ---
async def db_create_task(pool, user_id, title, description, priority, deadline):
    return await pool.fetchval(
        """
        INSERT INTO tasks (
            user_id,
            title,
            description,
            priority,
            deadline
        )
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        user_id,
        title,
        description,
        priority,
        deadline,
    )

async def get_tasks(pool, user_id: int):
    tasks = await pool.fetch(
        """
        SELECT id, user_id, title, description, priority, status, deadline, created_at, completed_at
        FROM tasks
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user_id
    )
    return tasks

async def get_task(pool, task_id: int, user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, title, description, priority, deadline,
                   status, completed_at, created_at
            FROM tasks
            WHERE id = $1 AND user_id = $2
            """,
            task_id, user_id,
        )
        return dict(row) if row else None


async def db_delete_task(pool, task_id: int, user_id: int):
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            DELETE FROM tasks
            WHERE id = $1 AND user_id = $2
            RETURNING id
            """,
            task_id,
            user_id,
        )
        return result is not None


async def db_edit_status(pool, task_id: int, user_id: int):
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Получаем текущий статус задачи
            row = await conn.fetchrow(
                """
                SELECT status
                FROM tasks
                WHERE id = $1 AND user_id = $2
                """,
                task_id, user_id,
            )

            if row is None:
                return None

            current_status = row["status"]

            if current_status == "active":
                # Переключаем на completed и ставим текущую дату/время
                updated = await conn.fetchrow(
                    """
                    UPDATE tasks
                    SET status = 'completed',
                        completed_at = NOW()
                    WHERE id = $1 AND user_id = $2
                    RETURNING id, status, completed_at
                    """,
                    task_id, user_id,
                )
            else:
                # Переключаем обратно на active и обнуляем completed_at
                updated = await conn.fetchrow(
                    """
                    UPDATE tasks
                    SET status = 'active',
                        completed_at = NULL
                    WHERE id = $1 AND user_id = $2
                    RETURNING id, status, completed_at
                    """,
                    task_id, user_id,
                )

            return dict(updated) if updated else None


async def db_edit_task(pool, task_id: int, user_id: int, field: str, value):
    allowed = {"title", "description", "priority", "deadline"}
    if field not in allowed:
        raise ValueError(f"Field {field} is not allowed")

    async with pool.acquire() as conn:
        query = f"UPDATE tasks SET {field} = $1 WHERE id = $2 AND user_id = $3 RETURNING id"
        return await conn.fetchval(query, value, task_id, user_id)

async def get_task_statistics(pool, user_id):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'completed') AS completed_count,
                COUNT(*) FILTER (WHERE status = 'active') AS active_count,
                COUNT(*) AS total_count
            FROM tasks
            WHERE user_id = $1
            """,
            user_id,
        )
        return {
            "completed": row["completed_count"] or 0,
            "active": row["active_count"] or 0,
            "total": row["total_count"] or 0,
        }

# --- Таблица users ---
async def get_notifications_enabled(pool, user_id: int) -> bool:
    value = await pool.fetchval(
        "SELECT notifications_enabled FROM users WHERE user_id = $1",
        user_id
    )
    return False if value is None else value

async def set_notifications_enabled(pool, user_id: int, enabled: bool):
    await pool.execute(
        """
        INSERT INTO users (user_id, notifications_enabled)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE
        SET notifications_enabled = EXCLUDED.notifications_enabled
        """,
        user_id, enabled,
    )

# --- Таблица task_reminders ---
async def get_reminders(pool):
    now = datetime.now()

    return await pool.fetch(
        """
        SELECT
            r.id AS reminder_id,
            r.reminder_type,
            t.id AS task_id,
            t.user_id,
            t.title,
            t.status AS task_status,
            t.deadline,
            r.deadline_snapshot,
            COALESCE(u.notifications_enabled, FALSE)
                AS notification_enabled
        FROM task_reminders AS r
        JOIN tasks AS t ON t.id = r.task_id
        LEFT JOIN users AS u ON u.user_id = t.user_id
        WHERE r.status = 'pending'
          AND r.scheduled_at <= $1
        ORDER BY r.scheduled_at
        LIMIT 100
        """,
        now,
    )

async def set_reminder_status(pool, reminder_id: int, status: str):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE task_reminders
            SET status = $2::VARCHAR,
                sent_at = CASE
                    WHEN $2::VARCHAR = 'sent'
                        THEN CURRENT_TIMESTAMP
                    ELSE sent_at
                END
            WHERE id = $1
              AND status = 'pending'
            """,
            reminder_id,
            status,
        )