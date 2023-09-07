import datetime
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
            util.remove_client(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                               emails)
    clients.update_many({'active': True, 'reseller': reseller['_id']}, {'$set': {'active': False}})
    resellers.update_one({'_id': reseller['_id']}, {'$set': {'enable': False}})

    text = '✅ نماینده مورد نظر با موفقیت *غیرفعال* شد.'
    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
