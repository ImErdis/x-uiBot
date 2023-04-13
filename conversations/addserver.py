from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import httpx
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler,
)
from configuration import Config
import util

config = Config('configuration.yaml')
db = config.get_db().servers

NAME, IP, PORT, USER, PASSWORD, INBOUND_ID, DOMAIN = range(7)
SERVER = {}
reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_add_server")]
])


async def add_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()

    await query.edit_message_text("لطفا اسم مورد نظرتون برای 🌎 سرور را ارسال کنید.", reply_markup=reply_markup)

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    if db.find_one({'name': update.message.text}):
        await update.message.reply_text('نام هر سرور باید متفاوت باشد لطفا نام جدید بفرستید', reply_markup=reply_markup)
        return NAME
    SERVER[f'{user.id}'] = {
        'name': update.message.text
    }

    await update.message.reply_text(
        "رواله, "
        "لطفا آیپی 🎛 سرور را بفرستید.", reply_markup=reply_markup
    )

    return IP


async def ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    SERVER[f'{user.id}']['ip'] = update.message.text

    await update.message.reply_text(
        "حله, "
        "لطفا پورت پنلو بفرستید.", reply_markup=reply_markup
    )

    return PORT


async def port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    SERVER[f'{user.id}']['port'] = int(update.message.text)

    await update.message.reply_text(
        "حله, "
        "لطفا یوزر پنل رو بفرستید.", reply_markup=reply_markup
    )

    return USER


async def user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    SERVER[f'{user.id}']['user'] = update.message.text

    await update.message.reply_text(
        "حله, "
        "لطفا پسورد پنلو بفرستید.", reply_markup=reply_markup
    )

    return PASSWORD


async def password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    SERVER[f'{user.id}']['password'] = update.message.text

    with httpx.Client() as client:
        body = {
            "username": SERVER[f'{user.id}']['user'],
            "password": SERVER[f'{user.id}']['password']
        }
        try:
            r = client.post("http://" + SERVER[f'{user.id}']['ip'] + ':' + str(SERVER[f'{user.id}']['port']) + '/login', data=body)
        except httpx.ConnectError:
            await update.message.reply_text('آدرس سرور اشتباه است! لطفا دوباره آدرس را بفرستید', reply_markup=reply_markup)
            return IP
        if not r.json()['success']:
            await update.message.reply_text('یوزر یا رمز اشتباه است! لطفا یوزر را بفرستید.',
                                            reply_markup=reply_markup)
            return USER


    await update.message.reply_text(
        "حله, "
        "لطفا آیدی اینباند رو بفرستید.", reply_markup=reply_markup
    )

    return INBOUND_ID


async def inbound_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    if db.find_one({'ip': SERVER[f'{user.id}']['ip'], 'inbound_id': int(update.message.text)}):
        await update.message.reply_text('این اینباند درحال حاضر اضافه شده هست '
                                        'لطفا دوباره اینباند آیدی را بفرستید', reply_markup=reply_markup)
        return INBOUND_ID
    SERVER[f'{user.id}']['inbound_id'] = int(update.message.text)
    try:
        util.get_inbound("http://" + SERVER[f'{user.id}']['ip'] + ':' + str(SERVER[f'{user.id}']['port']), SERVER[f'{user.id}']['user'], SERVER[f'{user.id}']['password'], int(update.message.text))
    except ModuleNotFoundError:
        await update.message.reply_text(
            "این اینباند وجود ندارد لطفا آیدی اینباند دیگری را بفرستید",reply_markup=reply_markup
        )
        return INBOUND_ID

    await update.message.reply_text(
        "حله, "
        "لطفا دامنه یا آدرس سرور برای کانفیگ رو ارسال کنید.", reply_markup=reply_markup
    )

    return DOMAIN


async def domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    SERVER[f'{user.id}']['domain'] = update.message.text

    db.insert_one(SERVER[f'{user.id}'])
    del SERVER[f'{user.id}']

    await update.message.reply_text(
        "حله, "
        "سرور با موفقیت اضافه شد.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('پنل ادمین', callback_data="admin")]])
    )

    return ConversationHandler.END


async def cancel_add_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query

    await query.answer()
    await query.edit_message_text('لطفا برای بازگشت /start یا دکمه زیر را فشار دهید', reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))
    user = query.from_user
    if SERVER.get(f'{user.id}'):
        del SERVER[f'{user.id}']

    return ConversationHandler.END


conv_handler = ConversationHandler(per_message=False,
    entry_points=[CallbackQueryHandler(add_server, pattern='^add_server$')],
    states={
        NAME: [MessageHandler(filters.TEXT, name)],
        IP: [MessageHandler(filters.Regex("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"), ip)],
        PORT: [MessageHandler(filters.Regex("^\d{1,6}$"), port)],
        USER: [MessageHandler(filters.TEXT, user)],
        PASSWORD: [MessageHandler(filters.TEXT, password)],
        INBOUND_ID: [MessageHandler(filters.Regex("^\d{1,6}$"), inbound_id)],
        DOMAIN: [MessageHandler(filters.TEXT, domain)],
    },
    fallbacks=[CallbackQueryHandler(cancel_add_server, pattern="^cancel_add_server$")],
)
