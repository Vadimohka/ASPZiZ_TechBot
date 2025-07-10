from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message()
async def unknown_command(message: types.Message):
    # Если это команда, но она не распознана, отвечаем "Неизвестная команда"
    if message.text and message.text.startswith("/"):
        await message.answer("Неизвестная команда. Введите /help для списка команд.")
