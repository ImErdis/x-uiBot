import base64
import json

from bson import ObjectId
from flask import Flask, request

import util
from configuration import Config

config = Config('configuration.yaml')
config.show_label()

svs = config.get_db().servers
groups = config.get_db().groups
clients = config.get_db().clients

app = Flask(__name__)


@app.route('/subscription', methods=['GET'])
async def response():
    uuid = request.args.get('uuid', default='', type=str)
    if not uuid:
        return '<p>Not Found</p>'
    client = clients.find_one({'_id': uuid})
    if client:
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
        text = '\n'.join(serv)
        return text
    return '<p>Not Found</p>'


app.run(host='0.0.0.0', port=80, threaded=True)
