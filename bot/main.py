import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from . import handlers
from .scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    token = os.environ.get("BOT_TOKEN_BANK")
    if not token:
        raise SystemExit("BOT_TOKEN_BANK is not set (see .env.example)")

    async def post_init(app: Application) -> None:
        setup_scheduler(app)

    application = Application.builder().token(token).post_init(post_init).build()

    application.add_handler(CommandHandler("start", handlers.cmd_start))
    application.add_handler(CallbackQueryHandler(handlers.on_callback, pattern=r"^bank:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text))

    logger.info("Bank bot starting...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
