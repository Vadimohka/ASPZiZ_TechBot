import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAMES = set(x.strip().lower() for x in os.getenv("ADMIN_USERNAMES", "").split(",") if x.strip())
DATABASE_PATH = "helpdesk.sqlite3"
