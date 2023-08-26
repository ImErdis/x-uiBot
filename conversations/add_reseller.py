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

RESELLER = {}

USER_ID, PPG, PREPAYMENT = range(3)


async def get_reseller_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()

    text = "⚠️ لطفا *آیدی تلگرامی نمایندگی* رو ارسال کنید."

    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return USER_ID


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the reseller id"""

    RESELLER[update.message.from_user.id] = {
        'id': update.message.text,
        'ppg': 0,
        'prepayment': True
    }

    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "💸 لطفا هزینه پرداختی برای *هر گیگ* برای نماینده انتخاب کنید. (تومان)"

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return PPG


async def ppg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the reseller ppg"""

    RESELLER[update.message.from_user.id]['ppg'] = update.message.text

    keyboard = [[InlineKeyboardButton("✅" if RESELLER[update.message.from_user.id]['prepayment'] else "❌",
                                      callback_data='add_reseller_prepayment'),
                 InlineKeyboardButton("پیش‌پرداخت", callback_data='add_reseller_ppg')],
                [InlineKeyboardButton("✅ اضافه کردن نماینده", callback_data='add_reseller_done')],
                [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """🔄 لطفا مشخص کنید که نماینده *پیش‌پرداخت* است یا خیر.

_(پیش‌پرداخت بودن به معنا این است که هزینه از حساب کم میشه و سپس به نماینده اکانت داده میشه)_"""

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return PREPAYMENT


async def pre_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores if reseller is done"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == 'add_reseller_done':
        text = "✅ نماینده با موفقیت اضافه شد."
        keyboard = [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        add_user(RESELLER[user.id]['id'], RESELLER[user.id]['prepayment'], RESELLER[user.id]['ppg'])
        return ConversationHandler.END

    RESELLER[user.id]['prepayment'] = not RESELLER[user.id]['prepayment']

    keyboard = [[InlineKeyboardButton("✅" if RESELLER[user.id]['prepayment'] else "❌",
                                      callback_data='add_reseller_prepayment'),
                 InlineKeyboardButton("پیش‌پرداخت", callback_data='add_reseller_ppg')],
                [InlineKeyboardButton("✅ اضافه کردن نماینده", callback_data='add_reseller_done')],
                [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """🔄 لطفا مشخص کنید که نماینده *پیش‌پرداخت* است یا خیر.

    _(پیش‌پرداخت بودن به معنا این است که هزینه از حساب کم میشه و سپس به نماینده اکانت داده میشه)_"""

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

conv_handler = ConversationHandler(per_message=False,
                                   entry_points=[CallbackQueryHandler(get_reseller_id, pattern='^add_reseller$')],
                                   states={
                                       USER_ID: [MessageHandler(filters.Regex("^\d"), user_id)],
                                       PPG: [MessageHandler(filters.Regex("^\d"), ppg)],
                                       PREPAYMENT: [CallbackQueryHandler(pre_payment, '^add_reseller_done$'),
                                                    CallbackQueryHandler(pre_payment, '^add_reseller_prepayment$')]
                                   },
                                   fallbacks=[CallbackQueryHandler(admin.admin, '^cancel$')], allow_reentry=True)