from aiogram import types, F, Router
from aiogram.filters import CommandStart
from db import DATABASE_PATH
import aiosqlite

router = Router()

async def add_ticket(user_id, chat_id, text, media_type, media_file_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO tickets (user_id, chat_id, text, media_type, media_file_id, status) VALUES (?, ?, ?, ?, ?, 'new')",
            (user_id, chat_id, text, media_type, media_file_id)
        )
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        return row[0]

@router.message(CommandStart())
async def on_start(message: types.Message):
    await message.answer("Добро пожаловать! Просто напишите сюда свою заявку текстом, фото, аудио или видео.")

@router.message(F.photo | F.video | F.audio | F.text)
async def handle_ticket(message: types.Message, bot):
    user = message.from_user
    # Бан проверять здесь (не реализовано для краткости)
    text = message.text or (message.caption or "")
    media_type = None
    media_file_id = None
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    elif message.audio:
        media_type = "audio"
        media_file_id = message.audio.file_id
    else:
        media_type = "text"
    ticket_id = await add_ticket(user.id, None, text, media_type, media_file_id)

    await message.answer("Джинны творят магию, ожидайте!")

    # Отправка в чат поддержки (заглушка, см. ниже)
    support_chat_ids = [-1001234567890]  # сюда - id ваших групп/чатов поддержки
    for chat_id in support_chat_ids:
        if media_type == "text":
            await bot.send_message(
                chat_id,
                f"Новая заявка!\n"
                f"Пользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
                f"Текст: {text}",
                reply_markup=gen_accept_kb(ticket_id)
            )
        elif media_type == "photo":
            await bot.send_photo(
                chat_id,
                media_file_id,
                caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\nТекст: {text}",
                reply_markup=gen_accept_kb(ticket_id)
            )
        elif media_type == "video":
            await bot.send_video(
                chat_id,
                media_file_id,
                caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\nТекст: {text}",
                reply_markup=gen_accept_kb(ticket_id)
            )
        elif media_type == "audio":
            await bot.send_audio(
                chat_id,
                media_file_id,
                caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\nТекст: {text}",
                reply_markup=gen_accept_kb(ticket_id)
            )

def gen_accept_kb(ticket_id):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="Принять", callback_data=f"accept_{ticket_id}")
    return kb.as_markup()

def setup_handlers(dp, bot):
    dp.include_router(router)
    # Здесь можно добавить router для админа и персонала
