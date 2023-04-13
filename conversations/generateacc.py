import base64
import datetime
import json
import uuid

import bson
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

servers = config.get_db().servers
subs = config.get_db().subscriptions
domain = config.website

NAME, SUBSCRIPTION = range(2)
reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_remove_server")]
])

ACCOUNT = {}


async def generate_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()

    await query.edit_message_text("لطفا اسم کاربر را ارسال کنید.", reply_markup=reply_markup)

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stores the sent server message"""

    ACCOUNT[update.message.from_user.id] = {
        'name': update.message.text,
        'subscription': None
    }

    sub_list = [x for x in subs.find({})]

    for sub in sub_list:
        for client in sub['clients']:
            if client['name'] == update.message.text:
                await update.message.reply_text('اسم هر اکانت باید جدا باشد لطفا اسم جدید بفرستید')
                return NAME
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'gasubscription_{x["name"]}'),
         InlineKeyboardButton(f'{len(x["clients"])}/{x["allowed_users"]}',
                              callback_data=f'gasubscription_{x["name"]}')] for x in sub_list
    ]
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_remove_server")])

    await update.message.reply_text(
        "رواله, "
        "اشتراکی ک قراره کاربرو بکنی توش رو انتخاب کن.", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SUBSCRIPTION


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    idi = uuid.uuid4()
    subscrpt = f'http://{domain}/subscription?uuid={idi}'
    name = query.data[15:]
    sub = subs.find_one({'name': name})
    client = {
        'name': ACCOUNT[query.from_user.id]['name'],
        '_id':
            str(idi),
        'servers': {},
        'usage_per_server': {},
        'usage': 0,
        'when': (datetime.datetime.now() + datetime.timedelta(seconds=int(sub['duration']))).timestamp(),
    }
    serv = []
    for server in sub['servers']:
        server = servers.find_one({'_id': server})
        inbound = util.get_inbound(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                                   server['inbound_id'])
        email = f'{uuid.uuid4()}'[:15]
        util.add_client(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                        server['inbound_id'],
                        util.generate_client(0, sub['traffic'], int(sub['duration']), email,
                                             idi))
        streamSettings = json.loads(inbound['streamSettings'])
        serv.append("`vmess://" + base64.b64encode(
            json.dumps(
                {'id': str(idi), 'aid': '0', 'v': '2', 'tls': streamSettings['security'], 'add': server['domain'],
                 'port': inbound['port'],
                 'type': streamSettings['tcpSettings']['header']['type'] if streamSettings['network'] == 'tcp' else
                 streamSettings['wsSettings']['headers'].get('type', ''),
                 'net': streamSettings['network'],
                 'path': streamSettings['tcpSettings']['header']['request']['path'] if streamSettings[
                                                                                           'network'] == 'tcp' else
                 streamSettings['wsSettings']['path'], 'host': '',
                 'ps': '@VingPN' + ' ' + sub['name'] + ' ' + server['name']}, sort_keys=True).encode(
                'utf-8')).decode() + '`\n' + f'{server["name"]}')
        client['servers'][f"{server['_id']}"] = email
        client['usage_per_server'][f"{server['_id']}"] = 0
    subs.update_one({'name': name}, {'$push': {
        'clients': client
    }})
    await query.edit_message_text(
        f"اسم اکانت: \n{ACCOUNT[query.from_user.id]['name']}\n\n" + '\n\n'.join(serv) + '\n\n🍩 لینک اشتراک: \n`' + subscrpt + '`', parse_mode='markdown'
    )
    del ACCOUNT[query.from_user.id]
    return ConversationHandler.END


async def cancel_remove_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query

    await query.answer()
    await query.edit_message_text('لطفا برای بازگشت /start یا دکمه زیر را فشار دهید', reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))

    return ConversationHandler.END


conv_handler = ConversationHandler(per_message=False,
                                   entry_points=[CallbackQueryHandler(generate_account, pattern='^generate_account$')],
                                   states={
                                       NAME: [MessageHandler(filters.TEXT, name)],
                                       SUBSCRIPTION: [CallbackQueryHandler(subscription, '^gasubscription_')]
                                   },
                                   fallbacks=[
                                       CallbackQueryHandler(cancel_remove_server, pattern="^cancel_remove_server$")],
                                   )
