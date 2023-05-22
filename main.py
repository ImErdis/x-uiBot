import base64
import json
import math
from datetime import datetime

import httpx
from bson import ObjectId
from telegram.ext._application import Application
from telegram.ext._callbackqueryhandler import CallbackQueryHandler

import threading
from handlers.index import index
from conversations.index import conversations
from callback.index import handlers
from telegram.ext import Updater, CommandHandler
from configuration import Config
import util

config = Config('configuration.yaml')
config.show_label()

servers = config.get_db().servers
subs = config.get_db().subscriptions
groups = config.get_db().groups
clients = config.get_db().clients


def do_every(interval, worker_func, iterations=0):
    if iterations != 1:
        threading.Timer(
            interval,
            do_every, [interval, worker_func, 0 if iterations == 0 else iterations - 1]
        ).start()

    worker_func()


def main():
    application = Application.builder().token(config.token).build()
    threading.Thread(target=do_every, args=(60, check_loop)).start()
    for k, v in index().items():
        application.add_handler(CommandHandler(k, v))
    for k, v in handlers().items():
        application.add_handler(CallbackQueryHandler(v, pattern=k))
    for convo in conversations():
        application.add_handler(convo)

    application.run_polling()


def check_loop():
    for server in servers.find({}):
        try:
            req = util.get_inbound(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                                   server['inbound_id'])

            client_stats = req['clientStats']
            for client_stat in client_stats:
                client = clients.find_one({f'servers.{server["_id"]}': client_stat['email'], 'active': True})
                if not client:
                    continue

                client['usage_per_server'][f'{server["_id"]}'] = (client_stat['down'] + client_stat['up']) / math.pow(
                    1024, 3)
                client['usage'] = sum(client['usage_per_server'].values())

                clients.update_one({'_id': client['_id']}, {'$set': client})

        except httpx.ConnectTimeout:
            continue

    for client in clients.find({'active': True}):
        subscription = subs.find_one({'_id': client['subscription']})
        if (client['usage'] >= subscription['traffic']) or (
                client['when'] < datetime.now().timestamp()):
            for server_id in client['servers'].keys():
                server = servers.find_one({'_id': ObjectId(server_id)})
                try:
                    util.remove_client(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                                       client['servers'][f"{server['_id']}"])
                except ModuleNotFoundError:
                    pass

            clients.update_one({'_id': client['_id']}, {'$set': {'active': False}, '$unset': {'servers': '', 'usage_per_server': '', 'when': ''}})


main()
