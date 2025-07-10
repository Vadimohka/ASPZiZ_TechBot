from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db import (
    is_admin, is_staff, set_chat_active, get_all_chats, log, get_new_tickets, get_admins,
    add_support_chat, is_ticket_published, register_publication, get_ticket, get_ticket_media, get_all_tickets,
    get_user_by_id, set_user_role
)
from handlers import gen_accept_kb
import logging

router = Router()
logger = logging.getLogger(__name__)

# ---- Декораторы ----
def staff_or_admin_only(handler):
    async def wrapper(*args, **kwargs):
        obj = None
        for arg in args:
            if isinstance(arg, types.Message) or isinstance(arg, types.CallbackQuery):
                obj = arg
                break
        obj = obj or kwargs.get('message') or kwargs.get('callback') or kwargs.get('event')
        if obj is None:
            logger.error("staff_or_admin_only: не найден message/callback")
            return
        user_id = obj.from_user.id
        user = await get_user_by_id(user_id)
        role = user[3] if user else None
        if role not in ('admin', 'staff'):
            await obj.answer("Доступ только для staff или admin.") if hasattr(obj, "answer") else await obj.message.answer("Доступ только для staff или admin.")
            return
        return await handler(*args, **kwargs)
    return wrapper

def admin_only(handler):
    async def wrapper(*args, **kwargs):
        obj = None
        for arg in args:
            if isinstance(arg, types.Message) or isinstance(arg, types.CallbackQuery):
                obj = arg
                break
        obj = obj or kwargs.get('message') or kwargs.get('callback') or kwargs.get('event')
        if obj is None:
            logger.error("admin_only: не найден message/callback")
            return
        user_id = obj.from_user.id
        if not await is_admin(user_id):
            await obj.answer("Доступ только для админа.") if hasattr(obj, "answer") else await obj.message.answer("Доступ только для админа.")
            return
        return await handler(*args, **kwargs)
    return wrapper

# ---- Команды ----
@router.message(Command("chats"))
@admin_only
async def show_chats(message: types.Message, **kwargs):
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
@admin_only
async def activate_chat(callback: types.CallbackQuery, **kwargs):
    chat_id = int(callback.data.split("_")[1])
    await set_chat_active(chat_id, True, approved_by=callback.from_user.id)
    await log("activate_chat", callback.from_user.id, f"Активация чата {chat_id}")
    await callback.answer("Чат активирован!")
    await callback.message.edit_reply_markup(None)

@router.callback_query(F.data.startswith("deactivate_"))
@admin_only
async def deactivate_chat(callback: types.CallbackQuery, **kwargs):
    chat_id = int(callback.data.split("_")[1])
    await set_chat_active(chat_id, False, approved_by=callback.from_user.id)
    await log("deactivate_chat", callback.from_user.id, f"Деактивация чата {chat_id}")
    await callback.answer("Чат деактивирован!")
    await callback.message.edit_reply_markup(None)

@router.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated, bot: Bot, **kwargs):
    if event.new_chat_member.user.id == (await bot.me()).id:
        await add_support_chat(event.chat.id, event.chat.title)
        admins = await get_admins()
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Одобрить", callback_data=f"approve_chat_{event.chat.id}")
        kb.button(text="🚫 Отклонить", callback_data=f"decline_chat_{event.chat.id}")
        for admin_id in admins:
            await bot.send_message(
                admin_id,
                f"Новый чат добавлен: {event.chat.title} (id: {event.chat.id}). Апрувить?",
                reply_markup=kb.as_markup()
            )

@router.callback_query(F.data.startswith("approve_chat_"))
@admin_only
async def approve_chat(callback: types.CallbackQuery, **kwargs):
    chat_id = int(callback.data.split("_")[2])
    await set_chat_active(chat_id, True, approved_by=callback.from_user.id)
    await callback.answer("Чат одобрен!")
    await callback.message.edit_reply_markup(None)

@router.callback_query(F.data.startswith("decline_chat_"))
@admin_only
async def decline_chat(callback: types.CallbackQuery, **kwargs):
    chat_id = int(callback.data.split("_")[2])
    await set_chat_active(chat_id, False, approved_by=callback.from_user.id)
    await callback.answer("Чат отклонён!")
    await callback.message.edit_reply_markup(None)

@router.message(Command("republish_new_tickets"))
@admin_only
async def republish_new_tickets(message: types.Message, bot: Bot = None, **kwargs):
    if not bot:
        bot = kwargs.get('bot')
    tickets = await get_new_tickets()
    chats = await get_all_chats()
    count = 0
    for ticket in tickets:
        for chat_id, title, is_active in chats:
            if is_active and not await is_ticket_published(ticket[0], chat_id):
                media = await get_ticket_media(ticket[0])
                group = []
                for m in media:
                    if m[0] == 'photo':
                        group.append(types.InputMediaPhoto(m[1], caption=ticket[3] if len(group) == 0 else None))
                    elif m[0] == 'video':
                        group.append(types.InputMediaVideo(m[1], caption=ticket[3] if len(group) == 0 else None))
                if group:
                    msgs = await bot.send_media_group(chat_id=chat_id, media=group)
                    await register_publication(ticket[0], chat_id, msgs[0].message_id)
                else:
                    msg = await bot.send_message(chat_id, ticket[3], reply_markup=gen_accept_kb(ticket[0]))
                    await register_publication(ticket[0], chat_id, msg.message_id)
                count += 1
    await message.answer(f"Опубликовано новых заявок: {count}")

@router.message(Command("all_history"))
@admin_only
async def all_history(message: types.Message, **kwargs):
    tickets = await get_all_tickets()
    if not tickets:
        await message.answer("Заявок не найдено.")
        return
    text_lines = []
    for t in tickets:
        ticket_id, user_id, username, created_at, status, text = t
        snippet = (text[:50] + "...") if text and len(text) > 50 else (text or "")
        text_lines.append(f"#{ticket_id} [{status}] {created_at} — @{username or user_id}: {snippet}")
    MAX_CHARS = 4000
    msg = ""
    for line in text_lines:
        if len(msg) + len(line) + 1 > MAX_CHARS:
            await message.answer(msg)
            msg = ""
        msg += line + "\n"
    if msg:
        await message.answer(msg)

@router.message(Command("help_admins"))
@staff_or_admin_only
async def help_admins(message: types.Message, **kwargs):
    help_text = """
<b>Админские и пользовательские команды Helpdesk-бота:</b>

<code>/start</code>
— Запускает бота, регистрирует пользователя с ролью <b>user</b>. После команды можно отправлять обращения (текст, фото, видео, голос).

<code>/who_am_i</code>
— Показывает ваш Telegram ID, username и роль в системе (роль всегда из базы данных).

<code>/my_history</code>
— Показывает все ваши обращения в систему: дата, статус (new/accepted/done), текст обращения. Для всех пользователей.

<code>/help</code>
— Краткая справка для пользователя.

<b>Только для staff или admin:</b>

<code>/chats</code>
— Список всех подключённых чатов поддержки. Можно включать/выключать чаты кнопками прямо из Telegram.

<code>/republish_new_tickets</code>
— Переотправляет все новые неразмещённые заявки во все активные чаты поддержки.

<code>/republish_ticket &lt;id&gt;</code>
— <b>Новая команда!</b> Переопубликовывает ЛЮБУЮ заявку по номеру (id) во все активные чаты поддержки, независимо от статуса и прошлых публикаций. Пример: <code>/republish_ticket 7</code>

<code>/all_history</code>
— Полная история всех заявок: номер, дата, статус, начало текста, отправитель. Если заявок много — разбивка по 4000 символов.

<code>/set_role &lt;user_id&gt; &lt;role&gt;</code>
— <b>Команда для админа!</b> Позволяет назначить роль user/staff/admin по Telegram ID.
Пример: <code>/set_role 123456 staff</code>
Пользователь должен быть в базе. Только для admin.

<b>Кнопки и callback-и (в чатах поддержки):</b>
• <b>Принять</b> — <b>Только staff</b> может взять заявку в работу (меняет статус на accepted, появляется подпись кто и когда взял).
• <b>Завершить</b> — Завершает заявку (статус done, приходит сообщение пользователю).

<b>Чат-менеджмент (только staff/admin):</b>
— При добавлении бота в новый чат, админам приходит запрос на одобрение/отклонение чата. Только после одобрения заявки из этого чата будут попадать в обработку.

<b>Прочее:</b>
• Все действия фиксируются в логах: создание, смена статуса, активация чатов, публикации и т.д.
• Роли (user, staff, admin) хранятся только в базе. Если пользователь появляется впервые — всегда "user" после /start.
• Только staff/admin могут управлять заявками, чатами, переотправлять заявки и видеть историю всех тикетов.

<b>Если нужна справка по конкретной команде — просто напиши её название в чат!</b>
"""
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("set_role"))
@admin_only
async def set_role(message: types.Message, **kwargs):
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /set_role <telegram_id> <role>\nПример: /set_role 123456 staff")
        return
    telegram_id, role = parts[1], parts[2]
    if role not in ("user", "staff", "admin"):
        await message.answer("Роль должна быть одной из: user, staff, admin")
        return
    user = await get_user_by_id(int(telegram_id))
    if not user:
        await message.answer(f"Пользователь с Telegram ID {telegram_id} не найден.")
        return
    await set_user_role(int(telegram_id), role)
    await message.answer(f"Роль пользователя {telegram_id} изменена на {role}.")

@router.message(Command("republish_ticket"))
@admin_only
async def republish_ticket(message: types.Message, bot: Bot = None, **kwargs):
    cmd_text = message.text.strip().split()
    if len(cmd_text) < 2 or not cmd_text[1].isdigit():
        await message.answer("Используй: /republish_ticket <id_заявки>")
        return
    ticket_id = int(cmd_text[1])
    ticket = await get_ticket(ticket_id)
    if not ticket:
        await message.answer(f"Заявка #{ticket_id} не найдена.")
        return
    chats = await get_all_chats()
    count = 0
    for chat_id, title, is_active in chats:
        if is_active:
            media = await get_ticket_media(ticket_id)
            group = []
            for m in media:
                if m[0] == 'photo':
                    group.append(types.InputMediaPhoto(m[1], caption=ticket[3] if len(group) == 0 else None))
                elif m[0] == 'video':
                    group.append(types.InputMediaVideo(m[1], caption=ticket[3] if len(group) == 0 else None))
            if group:
                msgs = await bot.send_media_group(chat_id=chat_id, media=group)
                await register_publication(ticket_id, chat_id, msgs[0].message_id)
            else:
                msg = await bot.send_message(chat_id, ticket[3], reply_markup=gen_accept_kb(ticket_id))
                await register_publication(ticket_id, chat_id, msg.message_id)
            count += 1
    await message.answer(f"Заявка #{ticket_id} переопубликована в {count} чат(ах).")
