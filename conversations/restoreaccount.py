import base64
import datetime
import json
import uuid
from uuid import UUID


def is_valid_uuid(uuid_to_test, version=4):
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


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
groups = config.get_db().groups
clients = config.get_db().clients
domain = config.website

NAME, GROUP, SUBSCRIPTION, EXTRASTEP = range(4)
reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_remove_server")]
])

ACCOUNT = {}


async def generate_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()

    await query.edit_message_text("لطفا اسم کاربر یا uuid خود را ارسال کنید.", reply_markup=reply_markup)

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    print(is_valid_uuid(update.message.text))
    if is_valid_uuid(update.message.text):
        print('Im here')
        ACCOUNT[update.message.from_user.id] = {
            '_id': update.message.text,
            'subscription': None
        }
    else:
        ACCOUNT[update.message.from_user.id] = {
            'name': update.message.text,
            'subscription': None
        }

    if '_id' in ACCOUNT[update.message.from_user.id]:
        clientDoc = clients.find_one({'_id': ACCOUNT[update.message.from_user.id]['_id']})
    else:
        clientDoc = clients.find_one({'name': ACCOUNT[update.message.from_user.id]['name']})
    if clientDoc:
        ACCOUNT[update.message.from_user.id]['name'] = clientDoc['name']
        ACCOUNT[update.message.from_user.id]['_id'] = clientDoc['_id']
    if not clientDoc and not is_valid_uuid(update.message.text):
        await update.message.reply_text('لطفا از آپشن ساخت اکانت استفاده کنید ' +
                                        'لطفا برای بازگشت /start یا دکمه زیر را فشار دهید',
                                        reply_markup=InlineKeyboardMarkup(
                                            [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))

        return ConversationHandler.END
    if not clientDoc and is_valid_uuid(update.message.text):
        await update.message.reply_text('لطفا اسم مورد نظر خودتون رو برای اکانت بفرستید.', reply_markup=reply_markup)
        return EXTRASTEP

    group_list = [x for x in groups.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'group_{x["name"]}')] for x in group_list if
        x['status'] == "Active"
    ]
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_create_subscription")])

    await update.message.reply_text("گروه مورد نظر را انتخاب کنید", reply_markup=InlineKeyboardMarkup(keyboard))

    return GROUP


async def extrastep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stores the sent server message"""

    ACCOUNT[update.message.from_user.id]['name'] = update.message.text

    if clients.find_one({'name': update.message.text}):
        await update.message.reply_text('اسم هر اکانت باید جدا باشد لطفا اسم جدید بفرستید')
        return EXTRASTEP

    group_list = [x for x in groups.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'group_{x["name"]}')] for x in group_list if
        x['status'] == "Active"
    ]
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_create_subscription")])

    await update.message.reply_text("گروه مورد نظر را انتخاب کنید", reply_markup=InlineKeyboardMarkup(keyboard))

    return GROUP


async def group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    sub_list = [x for x in subs.find({'group': query.data[6:]})]
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'gasubscription_{x["name"]}_{x["group"]}'),
         InlineKeyboardButton(f'{clients.count_documents({"subscription": x["_id"]})}',
                              callback_data=f'gasubscription_{x["name"]}_{x["group"]}')] for x in sub_list
    ]
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_remove_server")])

    await query.edit_message_text(
        "رواله, "
        "اشتراکی ک قراره کاربرو بکنی توش رو انتخاب کن.", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SUBSCRIPTION


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    clientDoc = clients.find_one({'name': ACCOUNT[query.from_user.id]['name']})
    idi = uuid.UUID(ACCOUNT[query.from_user.id]['_id'])
    sub = subs.find_one({'name': query.data.split('_')[1], 'group': query.data.split('_')[2]})
    client = {
        'name': ACCOUNT[query.from_user.id]['name'],
        '_id':
            str(idi),
        'servers': {},
        'usage_per_server': {},
        'active': True,
        'subscription': sub['_id'],
        'usage': 0,
        'when': (datetime.datetime.now() + datetime.timedelta(seconds=int(sub['duration']))).timestamp(),
    }
    serv = []
    group = groups.find_one({'name': sub['group']})
    for server in group['servers']:
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
                 'ps': client['name'] + ' ' + sub['name'] + ' ' + server['name']}, sort_keys=True).encode(
                'utf-8')).decode() + '`\n' + f'{server["name"]}')
        client['servers'][f"{server['_id']}"] = email
        client['usage_per_server'][f"{server['_id']}"] = 0
    clients.insert_one(client) if not clientDoc else clients.update_one({'name': ACCOUNT[query.from_user.id]['name']},
                                                                        {'$set': client})
    await query.edit_message_text(
        f"اسم اکانت: \n{ACCOUNT[query.from_user.id]['name']}\n\n" + '\n\n'.join(
            serv) + '\n\n🍩 لینک اشتراک: \n`' + f'http://{domain}/subscription?uuid={idi}' + '`', parse_mode='markdown'
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
                                   entry_points=[CallbackQueryHandler(generate_account, pattern='^restore_account$')],
                                   states={
                                       NAME: [MessageHandler(filters.TEXT, name)],
                                       GROUP: [CallbackQueryHandler(group, pattern='^group_')],
                                       SUBSCRIPTION: [CallbackQueryHandler(subscription, '^gasubscription_')],
                                       EXTRASTEP: [MessageHandler(filters.TEXT, extrastep)]
                                   },
                                   fallbacks=[
                                       CallbackQueryHandler(cancel_remove_server, pattern="^cancel_remove_server$")],
                                   )
