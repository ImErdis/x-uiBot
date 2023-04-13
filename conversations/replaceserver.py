import datetime

import httpx
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler,
)

import util
from configuration import Config

config = Config('configuration.yaml')

db = config.get_db().servers
subscriptions = config.get_db().subscriptions

IP, PORT, USER, PASSWORD, INBOUND_ID, DOMAIN = range(6)
reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_remove_server")]
])

SERVER = {}


async def replaceserver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()
    SERVER[f'{query.from_user.id}'] = {
        '_id': query.data[14:]
    }

    await query.edit_message_text("لطفا آیپی جدید 🌎 سرور را ارسال کنید.", reply_markup=reply_markup)

    return IP


async def ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    SERVER[f'{user.id}']['ip'] = update.message.text

    await update.message.reply_text("حالا پورت پنل سرور", reply_markup=reply_markup)

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
            r = client.post("http://" + SERVER[f'{user.id}']['ip'] + ':' + str(SERVER[f'{user.id}']['port']) + '/login',
                            data=body)
        except httpx.ConnectError:
            await update.message.reply_text('آدرس سرور اشتباه است! لطفا دوباره آدرس را بفرستید',
                                            reply_markup=reply_markup)
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
        util.get_inbound("http://" + SERVER[f'{user.id}']['ip'] + ':' + str(SERVER[f'{user.id}']['port']),
                         SERVER[f'{user.id}']['user'], SERVER[f'{user.id}']['password'], int(update.message.text))
    except ModuleNotFoundError:
        await update.message.reply_text(
            "این اینباند وجود ندارد لطفا آیدی اینباند دیگری را بفرستید", reply_markup=reply_markup
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

    for sub in subscriptions.find({}):
        if ObjectId(SERVER[f'{user.id}']['_id']) in sub['servers']:
            for client in sub['clients']:
                util.add_client(f'http://{SERVER[f"{user.id}"]["ip"]}:{SERVER[f"{user.id}"]["port"]}', SERVER[f"{user.id}"]['user'], SERVER[f"{user.id}"]['password'],
                                SERVER[f"{user.id}"]['inbound_id'],
                                util.generate_client(0, sub['traffic'],
                                                     client['when'] - datetime.datetime.now().timestamp(), client['servers'][f'{SERVER[f"{user.id}"]["_id"]}'],
                                                     client['_id']))

    id = ObjectId(SERVER[f'{user.id}']["_id"])
    del SERVER[f'{user.id}']["_id"]
    db.update_one({'_id': id}, {'$set': SERVER[f'{user.id}']})
    del SERVER[f'{user.id}']

    await update.message.reply_text(
        "حله, "
        "سرور با موفقیت جایگذین شد.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('پنل ادمین', callback_data="admin")]])
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
                                   entry_points=[CallbackQueryHandler(replaceserver, pattern='^replaceserver_')],
                                   states={
                                       IP: [MessageHandler(filters.Regex("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"), ip)],
                                       PORT: [MessageHandler(filters.Regex("^\d{1,6}$"), port)],
                                       USER: [MessageHandler(filters.TEXT, user)],
                                       PASSWORD: [MessageHandler(filters.TEXT, password)],
                                       INBOUND_ID: [MessageHandler(filters.Regex("^\d{1,6}$"), inbound_id)],
                                       DOMAIN: [MessageHandler(filters.TEXT, domain)],
                                   },
                                   fallbacks=[
                                       CallbackQueryHandler(cancel_remove_server, pattern="^cancel_remove_server$")],
                                   )
