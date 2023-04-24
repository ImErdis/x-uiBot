import base64
import json
import math
from datetime import datetime

import httpx
from telegram.ext._application import Application
from telegram.ext._callbackqueryhandler import CallbackQueryHandler

from handlers.index import index
from conversations.index import conversations
from callback.index import handlers
from telegram.ext import Updater, CommandHandler
from configuration import Config
import util

config = Config('configuration.yaml')
config.show_label()

svs = config.get_db().servers
subs = config.get_db().subscriptions


def main():
    application = Application.builder().token(config.token).build()
    job_queue = application.job_queue
    job_queue.run_repeating(check_loop, interval=60, first=10)
    for k, v in index().items():
        application.add_handler(CommandHandler(k, v))
    for k, v in handlers().items():
        application.add_handler(CallbackQueryHandler(v, pattern=k))
    for convo in conversations():
        application.add_handler(convo)

    application.run_polling()


async def check_loop(bot):
    subscriptions = subs.find({})
    for subscription in subscriptions:
        servers = subscription['servers']
        clients = subscription['clients']
        for server in servers:
            server = svs.find_one({'_id': server})
            try:
                e = util.get_inbound(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                                     server['inbound_id'])
            except httpx.ConnectTimeout:
                pass
            client_stats = e['clientStats']
            for client_stat in client_stats:
                for client in clients:
                    if not client.get('usage_per_server', None):
                        client['usage_per_server'] = {}
                    try:
                        if client_stat['email'] in client['servers'].values():
                            client['usage_per_server'][f'{server["_id"]}'] = client_stat['down'] / math.pow(1024, 3) + \
                                                                             client_stat['up'] / math.pow(
                                1024, 3)
                            client['usage'] = sum(client['usage_per_server'].values())
                    except AttributeError:
                        pass

        subs.update_one({'_id': subscription['_id']}, {'$set': {'clients': clients}})
    for subscription in subscriptions:
        for client in subscription['clients']:
            if (client['usage'] >= subscription['traffic']) or (
                    client['when'] < int(datetime.now().timestamp() * 1000)):
                for sv in subscription['servers']:
                    server = servers.find_one({'_id': sv})
                    try:
                        util.remove_client(f'http://{server["ip"]}:{server["port"]}', server['user'],
                                           server['password'], client['servers'][f"{server['_id']}"])
                    except ModuleNotFoundError:
                        pass
                subscription['clients'].remove(client)
        subscriptions.update_one({'name': subscription['name']}, {'$set': {'clients': subscription['clients']}})


main()
