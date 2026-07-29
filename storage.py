import aiosqlite
import config
from typing import Optional, List, Dict, Any

async def init_db():
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tracked_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER UNIQUE,
                slug TEXT,
                nickname TEXT,
                last_known_version TEXT,
                last_checked_at TIMESTAMP,
                forum_thread_id INTEGER
            )
        ''')
        await db.commit()

async def add_resource(resource_id: int, slug: str, nickname: str):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO tracked_resources (resource_id, slug, nickname) VALUES (?, ?, ?)',
            (resource_id, slug, nickname)
        )
        await db.commit()

async def remove_resource(nickname: str) -> bool:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute('DELETE FROM tracked_resources WHERE nickname = ?', (nickname,))
        await db.commit()
        return cursor.rowcount > 0

async def get_all_resources() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM tracked_resources')
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def update_resource_state(resource_id: int, version: str, thread_id: int = None):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        if thread_id is not None:
            await db.execute(
                'UPDATE tracked_resources SET last_known_version = ?, last_checked_at = CURRENT_TIMESTAMP, forum_thread_id = ? WHERE resource_id = ?',
                (version, thread_id, resource_id)
            )
        else:
            await db.execute(
                'UPDATE tracked_resources SET last_known_version = ?, last_checked_at = CURRENT_TIMESTAMP WHERE resource_id = ?',
                (version, resource_id)
            )
        await db.commit()

async def update_thread_id(resource_id: int, thread_id: int):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            'UPDATE tracked_resources SET forum_thread_id = ? WHERE resource_id = ?',
            (thread_id, resource_id)
        )
        await db.commit()
