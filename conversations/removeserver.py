from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler,
)
from configuration import Config

config = Config('configuration.yaml')

db = config.get_db().servers

NAME, IP, PORT, USER, PASSWORD, INBOUND_ID, USERS = range(7)
reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_remove_server")]
])


async def remove_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()

    await query.edit_message_text("لطفا اسم 🌎 سرور را ارسال کنید.", reply_markup=reply_markup)

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""

    db.delete_one({'name': update.message.text})

    await update.message.reply_text(
        "رواله, "
        "سرور موردنظر حذف شد.", reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]])
    )

    return ConversationHandler.END


async def cancel_remove_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query

    await query.answer()
    await query.edit_message_text('لطفا برای بازگشت /start یا دکمه زیر را فشار دهید', reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))

    return ConversationHandler.END


conv_handler = ConversationHandler(per_message=False,
    entry_points=[CallbackQueryHandler(remove_server, pattern='^remove_server')],
    states={
        NAME: [MessageHandler(filters.TEXT, name)]
    },
    fallbacks=[CallbackQueryHandler(cancel_remove_server, pattern="^cancel_remove_server$")],
)
