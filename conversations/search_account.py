import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler,
)

from callback import admin
from configuration import Config
from extra import resellerhandle

from extra.resellerhandle import add_user

config = Config('configuration.yaml')
resellers = config.get_db().resellers
clients = config.get_db().clients

_ID = range(1)


async def search_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()

    text = "⚠️ لطفا *UUID* یا *لینک اشتراک* اکانت رو ارسال کنید."

    keyboard = [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return _ID


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reseller = resellers.find_one({'_id': update.message.from_user.id})
    if not reseller:
        return ConversationHandler.END

    uuid4hex = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}', re.I)

    regex_check = uuid4hex.findall(update.message.text)
    if not bool(regex_check):
        return ConversationHandler.END

    if len(regex_check) > 1:
        return ConversationHandler.END

    client = clients.find_one({'_id': regex_check[0], 'reseller': update.message.from_user.id})
    if not bool(client):
        text = """⛔️ این اکانت تحت مالکیت شما *نیست*.

- _برای ادامه لطفا اکانت تحت مالکیت خودتان رو ارسال کنید._"""
        keyboard = [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return _ID

    keyboard = resellerhandle.generate_account_info_keyboard(client['_id'], reseller['_id'])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"""
        💼 اطلاعات *اکانت*. _(وضعیت: {'🟢 فعال' if client['active'] else '🔴 غیرفعال'})_

    - *📮 نام*: _{client['name']}_
    -  *🔑 آیدی*: `{client['_id']} `

    _🌐 به کانال ما (@VingPN) برای اطلاعات بیشتر مراجعه کنید._
        """
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return ConversationHandler.END


conv_handler = ConversationHandler(per_message=False,
                                   entry_points=[CallbackQueryHandler(search_account, pattern='^search_user$')],
                                   states={
                                       _ID: [MessageHandler(filters.Regex(
                                           "[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}"),
                                                            user_id)]
                                   },
                                   fallbacks=[CallbackQueryHandler(admin.admin, '^cancel$')], allow_reentry=True)
