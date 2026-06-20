import asyncio
import os

from dotenv import load_dotenv
from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from routers import router
import game as _game

load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    info = await bot.get_me()
    _game.bot_username = info.username

    dp = Dispatcher()
    dp.include_router(router)

    print(f"Bot @{info.username} started.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
