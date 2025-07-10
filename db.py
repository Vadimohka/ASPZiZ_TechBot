import aiosqlite
from config import DATABASE_PATH

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Пользователи
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            role TEXT, -- user, staff, admin
            is_banned INTEGER DEFAULT 0
        )""")
        # Чаты поддержки
        await db.execute("""
        CREATE TABLE IF NOT EXISTS support_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE,
            title TEXT,
            is_active INTEGER DEFAULT 0,
            approved_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Заявки
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            text TEXT,
            media_type TEXT,
            media_file_id TEXT,
            status TEXT, -- new, in_progress, done
            staff_id INTEGER,
            staff_message_id INTEGER,
            group_message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )""")
        # Логи
        await db.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            who_id INTEGER,
            details TEXT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.commit()

async def add_user(telegram_id, username, role="user"):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT OR IGNORE INTO users (telegram_id, username, role) VALUES (?, ?, ?)
        """, (telegram_id, username, role))
        await db.commit()

async def get_user_by_id(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        return await cur.fetchone()

async def is_admin(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=? AND role='admin'", (telegram_id,))
        return await cur.fetchone() is not None

async def get_admins():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT telegram_id FROM users WHERE role='admin'")
        return [r[0] for r in await cur.fetchall()]

async def add_support_chat(chat_id, title):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT OR IGNORE INTO support_chats (chat_id, title, is_active) VALUES (?, ?, 0)
        """, (chat_id, title))
        await db.commit()

async def set_chat_active(chat_id, active: bool, admin_id=None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        UPDATE support_chats SET is_active=?, approved_by=? WHERE chat_id=?
        """, (1 if active else 0, admin_id, chat_id))
        await db.commit()

async def get_active_chats():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT chat_id FROM support_chats WHERE is_active=1")
        return [r[0] for r in await cur.fetchall()]

async def get_all_chats():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT chat_id, title, is_active FROM support_chats")
        return await cur.fetchall()

async def save_ticket(user_id, text, media_type, media_file_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT INTO tickets (user_id, text, media_type, media_file_id, status)
        VALUES (?, ?, ?, ?, 'new')
        """, (user_id, text, media_type, media_file_id))
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        return (await cur.fetchone())[0]

async def update_ticket_group_message(ticket_id, group_message_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE tickets SET group_message_id=? WHERE id=?", (group_message_id, ticket_id))
        await db.commit()

async def get_new_tickets():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("""
        SELECT t.id, u.telegram_id, u.username, t.text, t.media_type, t.media_file_id 
        FROM tickets t
        JOIN users u ON t.user_id=u.id
        WHERE t.status='new'
        """)
        return await cur.fetchall()

async def set_ticket_accepted(ticket_id, staff_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        UPDATE tickets SET status='in_progress', staff_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='new'
        """, (staff_id, ticket_id))
        await db.commit()

async def set_ticket_done(ticket_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        UPDATE tickets SET status='done', updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (ticket_id,))
        await db.commit()

async def get_ticket(ticket_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
        return await cur.fetchone()

async def get_staff_history(staff_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("""
        SELECT * FROM tickets WHERE staff_id=? ORDER BY created_at DESC
        """, (staff_id,))
        return await cur.fetchall()

async def log(action, who_id, details):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT INTO logs (action, who_id, details) VALUES (?, ?, ?)
        """, (action, who_id, details))
        await db.commit()
