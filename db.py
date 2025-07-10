import aiosqlite
from config import DATABASE_PATH

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    role TEXT, -- 'user', 'staff', 'admin'
    is_banned INTEGER DEFAULT 0
);
"""
CREATE_TICKETS = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id INTEGER,
    text TEXT,
    media_type TEXT,
    media_file_id TEXT,
    status TEXT, -- 'new', 'in_progress', 'done'
    staff_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
"""
CREATE_LOGS = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT,
    who_id INTEGER,
    details TEXT,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_TICKETS)
        await db.execute(CREATE_LOGS)
        await db.commit()
