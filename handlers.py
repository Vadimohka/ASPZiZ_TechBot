from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import (
    add_user, get_user_by_id, save_ticket, update_ticket_group_message,
    get_active_chats, set_ticket_accepted, get_ticket, set_ticket_done,
    get_staff_history, log
)

router = Router()

def gen_accept_kb(ticket_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="Принять", callback_data=f"accept_{ticket_id}")
    return kb.as_markup()

def gen_done_kb(ticket_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="Задача выполнена", callback_data=f"done_{ticket_id}")
    return kb.as_markup()

@router.message(CommandStart())
async def on_start(message: Message):
    await add_user(message.from_user.id, message.from_user.username or "")
    await message.answer("Добро пожаловать! Просто напишите свою заявку текстом, фото, видео или голосом.")

@router.message(F.photo | F.video | F.audio | F.text)
async def handle_ticket(message: Message, bot):
    user = message.from_user
    await add_user(user.id, user.username or "")
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
    ticket_id = await save_ticket(user.id, text, media_type, media_file_id)
    await message.answer("Джинны творят магию, ожидайте!")

    # Рассылка по активным чатам
    chat_ids = await get_active_chats()
    for chat_id in chat_ids:
        if media_type == "text":
            msg = await bot.send_message(
                chat_id,
                f"Новая заявка!\nПользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\nТекст: {text}",
                reply_markup=gen_accept_kb(ticket_id)
            )
        elif media_type == "photo":
            msg = await bot.send_photo(
                chat_id,
                media_file_id,
                caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\nТекст: {text}",
                reply_markup=gen_accept_kb(ticket_id)
            )
        elif media_type == "video":
            msg = await bot.send_video(
                chat_id,
                media_file_id,
                caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\nТекст: {text}",
                reply_markup=gen_accept_kb(ticket_id)
            )
        elif media_type == "audio":
            msg = await bot.send_audio(
                chat_id,
                media_file_id,
                caption=f"Новая заявка!\nПользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\nТекст: {text}",
                reply_markup=gen_accept_kb(ticket_id)
            )
        else:
            continue
        await update_ticket_group_message(ticket_id, msg.message_id)

@router.callback_query(F.data.startswith("accept_"))
async def accept_ticket(callback: CallbackQuery, bot):
    ticket_id = int(callback.data.split("_")[1])
    user = callback.from_user
    await add_user(user.id, user.username or "", role="staff")
    ticket = await get_ticket(ticket_id)
    if not ticket or ticket[6] != 'new':  # status
        await callback.answer("Заявка уже принята другим сотрудником.")
        return
    await set_ticket_accepted(ticket_id, user.id)
    await log("accept", user.id, f"Принял заявку {ticket_id}")

    # Редактируем сообщение в чате
    new_text = callback.message.html_text + f"\n\nПринял: {user.full_name} ({user.username or user.id}) в {callback.message.date.strftime('%H:%M:%S')}"
    await callback.message.edit_text(new_text)
    await callback.message.edit_reply_markup(None)

    # Сообщаем сотруднику в ЛС
    await bot.send_message(
        user.id,
        f"Вы приняли заявку №{ticket_id}\nТекст: {ticket[3]}\n",
        reply_markup=gen_done_kb(ticket_id)
    )

    # Можно отправить медиа (если не текст)
    if ticket[4] == "photo":
        await bot.send_photo(user.id, ticket[5])
    elif ticket[4] == "video":
        await bot.send_video(user.id, ticket[5])
    elif ticket[4] == "audio":
        await bot.send_audio(user.id, ticket[5])

    await callback.answer("Вы приняли заявку! Информация в ЛС.")

@router.callback_query(F.data.startswith("done_"))
async def done_ticket(callback: CallbackQuery, bot):
    ticket_id = int(callback.data.split("_")[1])
    user = callback.from_user
    ticket = await get_ticket(ticket_id)
    if not ticket or ticket[6] != 'in_progress' or ticket[7] != user.id:
        await callback.answer("Вы не ответственны за эту заявку.")
        return
    await set_ticket_done(ticket_id)
    await log("done", user.id, f"Завершил заявку {ticket_id}")

    # Оповестить пользователя
    target_user_id = ticket[1]
    await bot.send_message(target_user_id, "Магия свершилась! Ваша заявка обработана.")
    await callback.answer("Заявка завершена!")

@router.message(Command("my_history"))
async def my_history(message: Message):
    staff_id = message.from_user.id
    history = await get_staff_history(staff_id)
    if not history:
        await message.answer("История пуста.")
        return
    text = "\n".join([
        f"Заявка #{t[0]}: {t[6]} ({t[9]})" for t in history  # id, status, updated_at
    ])
    await message.answer(text or "История пуста.")
