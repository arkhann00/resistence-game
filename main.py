import asyncio
import logging
import os

from dotenv import load_dotenv
from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import BotCommand

from routers import router
import game as _game

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]
PROXY = os.getenv("HTTPS_PROXY")  # optional: http://user:pass@host:port


async def _connect(bot: Bot, retries: int = 10, delay: float = 5.0):
    for attempt in range(1, retries + 1):
        try:
            return await bot.get_me()
        except (TelegramNetworkError, Exception) as e:
            if attempt == retries:
                raise
            log.warning("Попытка %d/%d — нет связи с Telegram: %s. Жду %ds…", attempt, retries, e, delay)
            await asyncio.sleep(delay)


async def main():
    session = AiohttpSession(proxy=PROXY) if PROXY else AiohttpSession()
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    info = await _connect(bot)
    _game.bot_username = info.username
    log.info("Бот @%s запущен.", info.username)

    await bot.set_my_commands([
        BotCommand(command="newgame", description="Начать новую игру (в группе)"),
        BotCommand(command="help",    description="Как играть через бота"),
        BotCommand(command="rules",   description="Правила игры"),
        BotCommand(command="endgame", description="Завершить игру досрочно (хост)"),
    ])

    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
