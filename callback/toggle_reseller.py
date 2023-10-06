import datetime
import json
import uuid

import httpx
from bson import ObjectId
from telegram import Update
from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram._inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import util
from configuration import Config
from extra import resellerhandle

config = Config('configuration.yaml')

db = config.get_db().clients
servers = config.get_db().servers
subscriptions = config.get_db().subscriptions
groups = config.get_db().groups
clients = config.get_db().clients
resellers = config.get_db().resellers


async def disable_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    _id = query.data.split('_')[2]
    reseller = resellers.find_one({'_id': int(_id)})
    if not reseller or not reseller.get('enable', True):
        return

    targets = [x['servers'] for x in
               clients.find({'active': True, 'reseller': reseller['_id']})]
    targets_per_server = {}
    for server in servers.find({}):
        targets_per_server[f'{server["_id"]}'] = []
    for target in targets:
        for server_id, email in target.items():
            targets_per_server[f'{server_id}'].append(email)

    for server_id, emails in targets_per_server.items():
        server = servers.find_one({'_id': ObjectId(server_id)})
        if len(emails) > 0:
            inbound = util.get_inbound(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                                       server['inbound_id'])
            settings = json.loads(inbound['settings'])
            while any([bool(x['email'] in emails) for x in settings['clients']]):
                for email in emails:
                    if any([x['email'] == email for x in settings['clients']]):
                        pass
                    else:
                        emails.remove(email)
                util.remove_client(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                                   emails)
                inbound = util.get_inbound(f'http://{server["ip"]}:{server["port"]}', server['user'],
                                           server['password'],
                                           server['inbound_id'])

                settings = json.loads(inbound['settings'])

    clients.update_many({'active': True, 'reseller': reseller['_id']}, {'$set': {'active': False, 'pause': True}})
    resellers.update_one({'_id': reseller['_id']}, {'$set': {'enable': False}})

    text = """⚠️ نمایندگی شما *غیرفعال* شده.

📨 لطفا برای پیگیری به *پشتیبانی* پیام بدید."""
    keyboard = [[InlineKeyboardButton("📞 ارتباط با ما", callback_data="contact-info")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    chat = await update.get_bot().get_chat(reseller['_id'])
    await chat.send_message(text, reply_markup=reply_markup, parse_mode='Markdown')


    text = '✅ نماینده مورد نظر با موفقیت *غیرفعال* شد.'
    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def enable_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    _id = query.data.split('_')[2]
    reseller = resellers.find_one({'_id': int(_id)})
    if not reseller or reseller.get('enable', True):
        return

    targets = []
    for client in clients.find({'active': False, 'reseller': reseller['_id'], 'pause': True}):
        clients.update_one({'_id': client['_id']}, {'$set': {'traffic': client['traffic'] - client['usage'], 'usage': 0}})
        for server_id, email in client['servers'].items():
            generated = util.generate_client(0, client['traffic'] - client['usage'], 1,
                                             email, client['_id'])
            generated['email'] = f'{uuid.uuid4()}'[:15]
            while clients.find_one({f'servers.{server_id}': generated['email']}):
                generated['email'] = f'{uuid.uuid4()}'[:15]
            generated['expiryTime'] = client['when'] * 1000
            generated['server_id'] = server_id
            targets.append(generated)
            clients.update_one({'_id': client['_id']},
                               {'$set': {f'servers.{server_id}': generated['email']}})
    targets_per_server = {}
    for server in servers.find({}):
        targets_per_server[f'{server["_id"]}'] = []
    for target in targets:
        server_id = f'{target["server_id"]}'
        del target["server_id"]
        targets_per_server[server_id].append(target)
    for server_id, all_of_clients in targets_per_server.items():
        server = servers.find_one({'_id': ObjectId(server_id)})
        if len(all_of_clients) > 0:
            util.add_client(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                            server['inbound_id'], all_of_clients)

    clients.update_many({'active': False, 'reseller': reseller['_id'], 'pause': True}, {'$set': {'active': True, 'pause': False}})
    resellers.update_one({'_id': reseller['_id']}, {'$set': {'enable': True}})

    text = """✅ نمایندگی شما *فعال* شد."""
    keyboard = [[InlineKeyboardButton("🖥️ پنل", callback_data="admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    chat = await update.get_bot().get_chat(reseller['_id'])
    await chat.send_message(text, reply_markup=reply_markup, parse_mode='Markdown')

    text = '✅ نماینده مورد نظر با موفقیت *فعال* شد.'
    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
