import base64
import json
import re
import uuid
from datetime import datetime
from typing import Literal

import util
from bson import ObjectId
from flask import Flask, request, render_template, Response
from multiprocessing import Process


from configuration import Config

config = Config('configuration.yaml')

clients = config.get_db().clients
svs = config.get_db().servers



def bytes_format(value):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0


def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """Format a date time"""
    if value is None:
        return ""
    if isinstance(value, float):
        value = datetime.fromtimestamp(value)
    return value.strftime(format)


app = Flask(__name__)


def links(client):
    serv = []
    for server_id in client['servers'].keys():
        server = svs.find_one({'_id': ObjectId(server_id)})
        try:
            inbound = util.get_inbound(f'http://{server["ip"]}:{server["port"]}', server['user'],
                                       server['password'],
                                       server['inbound_id'])
        except ModuleNotFoundError:
            # Not Implemented Yet
            pass
        streamSettings = json.loads(inbound['streamSettings'])
        serv.append("vmess://" + base64.b64encode(
            json.dumps({'id': client['_id'], 'aid': '0', 'v': '2', 'tls': streamSettings['security'],
                        'add': server['domain'],
                        'port': inbound['port'],
                        'type': streamSettings['tcpSettings']['header']['type'] if streamSettings[
                                                                                       'network'] == 'tcp' else
                        streamSettings['wsSettings']['headers'].get('type', ''),
                        'net': streamSettings['network'],
                        'path': streamSettings['tcpSettings']['header']['request']['path'] if
                        streamSettings['network'] == 'tcp' else streamSettings['wsSettings']['path'],
                        'host': '',
                        'ps': client['name'] + ' ' + server['name']}, sort_keys=True).encode(
                'utf-8')).decode())
    return serv


def generate_subscription(
        client,
        config_format: Literal["v2ray", "clash-meta", "clash"],
        as_base64: bool
) -> str:
    if config_format == 'v2ray':
        configs = "\n".join(links(client))
    else:
        raise ValueError(f'Unsupported format "{config_format}"')

    if as_base64:
        configs = base64.b64encode(configs.encode()).decode()

    return configs


app.jinja_env.filters['bytesformat'] = bytes_format
app.jinja_env.filters['datetime'] = format_datetime


@app.route('/subscription', methods=['GET'])
async def response():
    accept_header = request.headers.get("Accept", "")
    user_agent = request.headers.get("User-Agent", "")
    uid = request.args.get('uuid', default='', type=str)
    if not uid:
        return "", 204
    client = clients.find_one({'_id': uid, 'active': True})
    if not client:
        return "", 204
    current_time = datetime.now()
    link = links(client)
    links_json = json.dumps(link)
    formatted_links = links_json.replace('"', "'")
    if "text/html" in accept_header:
        return render_template('subscription.html', username=client['name'],
                               now=current_time,
                               expire=client['when'],
                               links=formatted_links, subscription_url='https://sub.nobodyvpn.com/subscription?uuid=' + client['_id'],
                               data_limit=client['traffic'] * 1024 ** 3,
                               used_traffic=client['usage'] * 1024 ** 3)

    def get_subscription_user_info(sub) -> dict:
        return {
            "upload": 0,
            "download": client['usage'] * 1024 ** 3,
            "total": client['traffic'] * 1024 ** 3,
            "expire": client['when'],
        }

    name = client['name']

    response_headers = {
        "content-disposition": f'attachment; filename="{name}"',
        "profile-update-interval": "12",
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(client).items()
            if val is not None
        )
    }

    if re.match('^([Cc]lash-verge|[Cc]lash-?[Mm]eta)', user_agent):
        conf = generate_subscription(client, config_format="clash-meta", as_base64=False)
        return Response(response=conf, content_type="text/yaml", headers=response_headers)

    elif re.match('^([Cc]lash|[Ss]tash)', user_agent):
        conf = generate_subscription(client, config_format="clash", as_base64=False)
        return Response(response=conf, content_type="text/yaml", headers=response_headers)

    else:
        conf = generate_subscription(client, config_format="v2ray", as_base64=True)
        return Response(response=conf, content_type="text/plain", headers=response_headers)


def run_flask():
    app.run(host='0.0.0.0', port=443)


if __name__ == '__main__':
    flask_process = Process(target=run_flask)
    flask_process.start()

