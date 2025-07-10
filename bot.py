import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db

async def main():
    await init_db()
    bot = Bot(BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    # Handlers
    from handlers import router as h_router
    from admin import router as a_router
    dp.include_router(h_router)
    dp.include_router(a_router)
    print("Helpdesk Bot is running.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
