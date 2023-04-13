from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram._inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram._update import Update
from configuration import Config

config = Config('configuration.yaml')


async def start(update: Update, context):
    """Sends a message with three inline buttons attached."""

    keyboard = [
        [InlineKeyboardButton("دریافت اشتراک تست", callback_data="test")],
    ]
    if update.message.from_user.id == config.admin:
        keyboard.append([
            InlineKeyboardButton("پنل ادمین", callback_data="admin")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("به ربات تستی ما خوش اومدی حالا خدافظ", reply_markup=reply_markup)
