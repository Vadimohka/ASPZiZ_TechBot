import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db

async def main():
    await init_db()
    bot = Bot(BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    # handlers import
    from handlers import setup_handlers
    setup_handlers(dp, bot)
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
