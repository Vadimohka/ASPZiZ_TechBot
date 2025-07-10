from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from db import get_user_by_id, get_user_tickets, add_or_update_user
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await add_or_update_user(message.from_user.id, message.from_user.username or "")

    await message.answer(
        "Добро пожаловать! Просто напишите свою заявку текстом, фото, видео или голосом. "
        "Для просмотра своих заявок используйте /my_history.\n"
        "Для помощи — /help."
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "<b>Доступные команды:</b>\n"
        "/help — показать справку\n"
        "/who_am_i — узнать свою роль и Telegram ID\n"
        "/my_history — посмотреть свои заявки\n"
        "Любое текстовое/медийное сообщение — создать заявку в поддержку"
    )

@router.message(Command("who_am_i"))
async def cmd_who_am_i(message: types.Message):
    user = await get_user_by_id(message.from_user.id)
    if user:
        # Предполагаем user = (id, telegram_id, username, role, ...)
        telegram_id = user[1]
        username = user[2]
        role = user[3]
        await message.answer(
            f"Ваш Telegram ID: <code>{telegram_id}</code>\n"
            f"Username: {username}\n"
            f"Роль в системе: <b>{role}</b>"
        )
    else:
        await message.answer(
            "Вы не зарегистрированы в системе.\n"
            "Появитесь в базе после первой заявки."
        )

@router.message(Command("my_history"))
async def cmd_my_history(message: types.Message):
    tickets = await get_user_tickets(message.from_user.id)
    if not tickets:
        await message.answer("У вас пока нет заявок.")
        return
    text_lines = []
    for t in tickets:
        ticket_id, created_at, status, text = t
        snippet = (text[:50] + "...") if text and len(text) > 50 else (text or "")
        text_lines.append(f"#{ticket_id} [{status}] — {snippet}")
    # Режем на сообщения до 4000 символов (ограничение Telegram)
    MAX_CHARS = 4000
    msg = ""
    for line in text_lines:
        if len(msg) + len(line) + 1 > MAX_CHARS:
            await message.answer(msg)
            msg = ""
        msg += line + "\n"
    if msg:
        await message.answer(msg)
