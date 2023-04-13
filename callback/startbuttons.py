from telegram import Update
from telegram.ext import ContextTypes
from ..configuration import Config

config = Config('configuration.yaml')


db = config.get_db().clients


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()


