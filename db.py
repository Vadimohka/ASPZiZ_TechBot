import aiosqlite
import logging
from config import DATABASE_PATH, ADMIN_USER_IDS

logger = logging.getLogger(__name__)

# Инициализация базы
async def init_db():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Таблица пользователей
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                role TEXT DEFAULT 'user'
            )""")
            # Таблица чатов поддержки
            await db.execute("""
            CREATE TABLE IF NOT EXISTS support_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE,
                title TEXT,
                is_active BOOLEAN DEFAULT 0,
                approved_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            # Таблица тикетов
            await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                text TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            # Медиа тикетов
            await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                type TEXT,
                file_id TEXT
            )""")
            # Где и что опубликовано
            await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                chat_id INTEGER,
                message_id INTEGER
            )""")
            # Логи
            await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                user_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

            # ---- ДОБАВЛЯЕМ АДМИНОВ ИЗ .env В users, если их нет ----
            for admin_id in ADMIN_USER_IDS:
                async with db.execute("SELECT 1 FROM users WHERE telegram_id = ?", (admin_id,)) as cursor:
                    exists = await cursor.fetchone()
                if not exists:
                    await db.execute(
                        "INSERT INTO users (telegram_id, username, role) VALUES (?, ?, ?)",
                        (admin_id, '', 'admin')
                    )

            await db.commit()
            logger.info("DB initialized")
    except Exception as e:
        logger.error(f"DB init error: {e}")

# --- USERS ---

async def add_or_update_user(telegram_id: int, username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, role)
            VALUES (?, ?, COALESCE((SELECT role FROM users WHERE telegram_id=?), 'user'))
            ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username
        """, (telegram_id, username, telegram_id))
        await db.commit()


async def get_user_by_id(telegram_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
            ) as cur:
                return await cur.fetchone()
    except Exception as e:
        logger.error(f"get_user_by_id error: {e}")

async def is_admin(telegram_id):
    from config import ADMIN_USER_IDS
    return telegram_id in ADMIN_USER_IDS

# --- SUPPORT CHATS ---

async def add_support_chat(chat_id, title):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO support_chats (chat_id, title) VALUES (?, ?)",
                (chat_id, title)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"add_support_chat error: {e}")

async def set_chat_active(chat_id, is_active, approved_by=None):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE support_chats SET is_active=?, approved_by=? WHERE chat_id=?",
                (1 if is_active else 0, approved_by, chat_id)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"set_chat_active error: {e}")

async def get_all_chats():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT chat_id, title, is_active FROM support_chats"
            ) as cur:
                return await cur.fetchall()
    except Exception as e:
        logger.error(f"get_all_chats error: {e}")
        return []

async def get_active_support_chats():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT chat_id FROM support_chats WHERE is_active=1"
            ) as cur:
                return await cur.fetchall()
    except Exception as e:
        logger.error(f"get_active_support_chats error: {e}")
        return []

async def get_admins():
    from config import ADMIN_USER_IDS
    return ADMIN_USER_IDS

# --- TICKETS ---

async def save_ticket(user_id, username, text):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "INSERT INTO tickets (user_id, username, text) VALUES (?, ?, ?)",
                (user_id, username, text)
            )
            await db.commit()
            return cur.lastrowid
    except Exception as e:
        logger.error(f"save_ticket error: {e}")

async def save_ticket_media(ticket_id, media: list):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            for m in media:
                await db.execute(
                    "INSERT INTO ticket_media (ticket_id, type, file_id) VALUES (?, ?, ?)",
                    (ticket_id, m['type'], m['file_id'])
                )
            await db.commit()
    except Exception as e:
        logger.error(f"save_ticket_media error: {e}")

async def get_ticket(ticket_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT * FROM tickets WHERE id=?", (ticket_id,)
            ) as cur:
                return await cur.fetchone()
    except Exception as e:
        logger.error(f"get_ticket error: {e}")

async def get_ticket_media(ticket_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT type, file_id FROM ticket_media WHERE ticket_id=?", (ticket_id,)
            ) as cur:
                return await cur.fetchall()
    except Exception as e:
        logger.error(f"get_ticket_media error: {e}")
        return []

async def register_publication(ticket_id, chat_id, message_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO ticket_publications (ticket_id, chat_id, message_id) VALUES (?, ?, ?)",
                (ticket_id, chat_id, message_id)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"register_publication error: {e}")

async def is_ticket_published(ticket_id, chat_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT id FROM ticket_publications WHERE ticket_id=? AND chat_id=?",
                (ticket_id, chat_id)
            ) as cur:
                return await cur.fetchone() is not None
    except Exception as e:
        logger.error(f"is_ticket_published error: {e}")
        return False

async def set_ticket_accepted(ticket_id, user_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE tickets SET status='accepted' WHERE id=? AND status='new'", (ticket_id,)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"set_ticket_accepted error: {e}")

async def set_ticket_done(ticket_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE tickets SET status='done' WHERE id=?", (ticket_id,)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"set_ticket_done error: {e}")

async def get_new_tickets():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT * FROM tickets WHERE status='new' ORDER BY created_at"
            ) as cur:
                return await cur.fetchall()
    except Exception as e:
        logger.error(f"get_new_tickets error: {e}")
        return []

async def get_all_tickets():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT id, user_id, username, created_at, status, text FROM tickets ORDER BY created_at DESC"
            ) as cur:
                rows = await cur.fetchall()
                logger.info(f"get_all_tickets: found {len(rows)} tickets")
                return rows
    except Exception as e:
        logger.error(f"get_all_tickets error: {e}")
        return []

async def get_user_tickets(user_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT id, created_at, status, text FROM tickets WHERE user_id=? ORDER BY created_at DESC", (user_id,)
            ) as cur:
                return await cur.fetchall()
    except Exception as e:
        logger.error(f"get_user_tickets error: {e}")
        return []


async def is_staff(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT role FROM users WHERE telegram_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None and row[0] == 'staff'


async def set_user_role(telegram_id: int, role: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?",
            (role, telegram_id)
        )
        await db.commit()



# --- LOGGING ---

async def log(action, user_id, details):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO logs (action, user_id, details) VALUES (?, ?, ?)",
                (action, user_id, details)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"log error: {e}")
