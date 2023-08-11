import json
import urllib.parse
import uuid
import httpx
import datetime
from configuration import Config

config = Config('configuration.yaml')

subs = config.get_db().subscriptions


def generate_client(limitIp, totalGB, expiryTime, email, idi=None) -> dict:
    if not idi:
        idi = uuid.uuid4()
    return {'id': f'{idi}',
            'alterId': 0,
            'email': email,
            'limitIp': limitIp,
            'totalGB': int(totalGB * 1024 * 1024 * 1024),
            'expiryTime': int((datetime.datetime.now() + datetime.timedelta(seconds=expiryTime)).timestamp() * 1000)}


def get_inbounds(url, username, password) -> dict:
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        r = client.post(url + '/login', data=body)
        r = client.post(url + '/xui/inbound/list', cookies=client.cookies)
        if not r.is_success:
            r = client.post(url + '/panel/inbound/list', cookies=client.cookies)
        return json.loads(r.content)['obj']


def update_inbound(url, username, password, idi, data):
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        r = client.post(f'{url}/xui/inbound/update/{idi}', json=data)
        if not r.is_success:
            r = client.post(f'{url}/panel/inbound/update/{idi}', json=data)
        return r.json()


def get_inbound(url: str, username: str, password: str, idi: int) -> dict:
    inbounds = get_inbounds(url, username, password)
    for inbound in inbounds:
        if inbound['id'] == idi:
            return inbound
    raise ModuleNotFoundError


def add_client(url, username, password, idi, client):
    data = get_inbound(url, username, password, idi)
    del data['id']
    del data['tag']
    del data['clientStats']
    settings = json.loads(data['settings'])
    settings['clients'].append(client)
    data['settings'] = json.dumps(settings)
    response = update_inbound(url, username, password, idi, data)
    return response


def remove_client(url, username, password, email):
    inbounds = get_inbounds(url, username, password)
    for inbound in inbounds:
        settings = json.loads(inbound['settings'])
        if any([x['email'] == email for x in settings['clients']]):
            idi = inbound['id']
            del inbound['id']
            inbound['clientStats'] = None
            for client in settings['clients']:
                if client['email'] == email:
                    settings['clients'].remove(client)
            inbound['settings'] = json.dumps(settings)
            response = update_inbound(url, username, password, idi, inbound)
            return response
    raise ModuleNotFoundError


def edit_client(url, username, password, email, client):
    inbounds = get_inbounds(url, username, password)
    for inbound in inbounds:
        settings = json.loads(inbound['settings'])
        if any([x['email'] == email for x in settings['clients']]):
            idi = inbound['id']
            del inbound['id']
            inbound['clientStats'] = None
            for ind, cl in enumerate(settings['clients']):
                if cl['email'] == email:
                    settings['clients'][ind] = client
            inbound['settings'] = json.dumps(settings)
            response = update_inbound(url, username, password, idi, inbound)
            return response
    raise ModuleNotFoundError


def get_client(url, username, password, email):
    inbounds = get_inbounds(url, username, password)
    for inbound in inbounds:
        settings = json.loads(inbound['settings'])
        if any([x['email'] == email for x in settings['clients']]):
            for client in settings['clients']:
                if client['email'] == email:
                    return client
    raise ModuleNotFoundError
