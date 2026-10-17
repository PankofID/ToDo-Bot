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

async def db_create_task(pool, user_id, title, description, priority, deadline):
    await pool.execute(
        """
        INSERT INTO tasks
            (user_id, title, description, priority, deadline)
        VALUES
            ($1, $2, $3, $4, $5)
        """,
        user_id,
        title,
        description,
        priority,
        deadline
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
            """,
            task_id, user_id,
        )
        return result == "DELETE 1"


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