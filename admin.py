from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import (
    is_admin, set_chat_active, get_all_chats, log, get_new_tickets, get_admins,
    add_user
)

router = Router()

def admin_only(handler):
    async def wrapper(message, *args, **kwargs):
        await add_user(message.from_user.id, message.from_user.username or "", role="admin")
        if not await is_admin(message.from_user.id):
            await message.answer("Доступ только для админа.")
            return
        return await handler(message, *args, **kwargs)
    return wrapper

@router.message(Command("chats"))
@admin_only
async def show_chats(message: types.Message):
    chats = await get_all_chats()
    if not chats:
        await message.answer("Нет подключённых чатов.")
        return
    text = ""
    kb = InlineKeyboardBuilder()
    for chat_id, title, is_active in chats:
        status = "✅ Активен" if is_active else "❌ Неактивен"
        text += f"{title or chat_id} ({chat_id}): {status}\n"
        if is_active:
            kb.button(text=f"Деактивировать {title or chat_id}", callback_data=f"deactivate_{chat_id}")
        else:
            kb.button(text=f"Активировать {title or chat_id}", callback_data=f"activate_{chat_id}")
    await message.answer(text, reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("activate_"))
async def activate_chat(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[1])
    await set_chat_active(chat_id, True, admin_id=callback.from_user.id)
    await log("activate_chat", callback.from_user.id, f"Активация чата {chat_id}")
    await callback.answer("Чат активирован!")
    await callback.message.edit_reply_markup(None)

@router.callback_query(F.data.startswith("deactivate_"))
async def deactivate_chat(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[1])
    await set_chat_active(chat_id, False, admin_id=callback.from_user.id)
    await log("deactivate_chat", callback.from_user.id, f"Деактивация чата {chat_id}")
    await callback.answer("Чат деактивирован!")
    await callback.message.edit_reply_markup(None)

@router.message(Command("republish_new_tickets"))
@admin_only
async def republish_new_tickets(message: types.Message, bot):
    tickets = await get_new_tickets()
    if not tickets:
        await message.answer("Нет непринятых заявок.")
        return
    chat_ids = await get_all_chats()
    chat_ids = [c[0] for c in chat_ids if c[2]]  # только активные
    count = 0
    for ticket_id, telegram_id, username, text, media_type, media_file_id in tickets:
        for chat_id in chat_ids:
            if media_type == "text":
                await bot.send_message(
                    chat_id,
                    f"Новая заявка!\nПользователь: <a href='tg://user?id={telegram_id}'>{username or telegram_id}\nТекст: {text}"
                )
            elif media_type == "photo":
                await bot.send_photo(
                    chat_id,
                    media_file_id,
                    caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={telegram_id}'>{username or telegram_id}\nТекст: {text}"
                )
            elif media_type == "video":
                await bot.send_video(
                    chat_id,
                    media_file_id,
                    caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={telegram_id}'>{username or telegram_id}\nТекст: {text}"
                )
            elif media_type == "audio":
                await bot.send_audio(
                    chat_id,
                    media_file_id,
                    caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={telegram_id}'>{username or telegram_id}\nТекст: {text}"
                )
            count += 1
    await log("republish", message.from_user.id, f"Репаблиш {count} заявок")
    await message.answer(f"Заявки опубликованы: {count}")

# Подтверждение чата при добавлении
@router.message(F.new_chat_members)
async def new_chat_member(message: types.Message, bot):
    for member in message.new_chat_members:
        if member.id == bot.id:
            from db import add_support_chat, get_admins
            await add_support_chat(message.chat.id, message.chat.title)
            for admin_id in await get_admins():
                kb = InlineKeyboardBuilder()
                kb.button(text="✅ Одобрить", callback_data=f"approve_chat_{message.chat.id}")
                kb.button(text="🚫 Отклонить", callback_data=f"reject_chat_{message.chat.id}")
                await bot.send_message(
                    admin_id,
                    f"Бот добавлен в новый чат: {message.chat.title} (id: {message.chat.id}). Апрувить публикацию заявок?",
                    reply_markup=kb.as_markup()
                )

@router.callback_query(F.data.startswith("approve_chat_"))
async def approve_chat(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    await set_chat_active(chat_id, True, admin_id=callback.from_user.id)
    await log("approve_chat", callback.from_user.id, f"Апрув чата {chat_id}")
    await callback.answer("Чат одобрен и активирован!")
    await callback.message.edit_reply_markup(None)

@router.callback_query(F.data.startswith("reject_chat_"))
async def reject_chat(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    await set_chat_active(chat_id, False, admin_id=callback.from_user.id)
    await log("reject_chat", callback.from_user.id, f"Отклонение чата {chat_id}")
    await callback.answer("Чат не активирован!")
    await callback.message.edit_reply_markup(None)
