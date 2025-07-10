import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in .env file or environment!")

ADMIN_USER_IDS = [
    int(i.strip()) for i in os.getenv("ADMIN_USER_IDS", "").split(",") if i.strip()
]

# Абсолютный путь внутри контейнера (volume ./data:/app/data)
DATABASE_PATH = "/app/data/helpdesk.sqlite3"

# Только user_id в ADMIN_USER_IDS обладают абсолютной ролью admin!
