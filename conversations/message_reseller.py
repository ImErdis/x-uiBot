import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler,
)

from callback import admin
from configuration import Config

from extra.resellerhandle import add_user

config = Config('configuration.yaml')
resellers = config.get_db().resellers

message_handler = {}

MESSAGE = range(1)


async def message_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()
    data = query.data
    if data.split('_')[2] == 'all':
        text = "⚠️ لطفا *پیام همگانی* رو ارسال کنید."
        message_handler[f'{query.from_user.id}'] = {
            'mode': 'everyone',
            'target': 'all'
        }
    else:
        text = "⚠️ لطفا *پیام شخصی* رو ارسال کنید."
        message_handler[f'{query.from_user.id}'] = {
            'mode': 'single',
            'target': int(data.split('_')[2])
        }

    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return MESSAGE


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = update.message.text

    failed = []
    rs = resellers.find({}) if message_handler[f'{update.message.from_user.id}']['mode'] =='everyone' else resellers.find({'_id': message_handler[f'{update.message.from_user.id}']['target']})
    for reseller in rs:
        try:
            chat = await update.get_bot().get_chat(reseller["_id"])
            await chat.send_message(message_text)
        except telegram.error.BadRequest:
            failed.append(reseller)
    if failed:
        text = '🔴 *پیام به لیست زیر ارسال نشد*:\n\n'
        for fail in failed:
            text += f'_{fail["_id"]}_'
    else:
        text = '✅ *پیام با موفقیت ارسال گردید*.'
    keyboard = [[InlineKeyboardButton("🖥️ پنل", callback_data="admin")]]
    del message_handler[f'{update.message.from_user.id}']
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return ConversationHandler.END


conv_handler = ConversationHandler(per_message=False,
                                   entry_points=[CallbackQueryHandler(message_reseller, pattern='^message_reseller_')],
                                   states={
                                       MESSAGE: [MessageHandler(filters.TEXT, message)]
                                   },
                                   fallbacks=[CallbackQueryHandler(admin.admin, '^cancel$')], allow_reentry=True)
