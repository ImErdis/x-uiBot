import datetime

from configuration import Config

config = Config('configuration.yaml')
config.show_label()

svs = config.get_db().servers
subs = config.get_db().subscriptions
groups = config.get_db().groups
clients = config.get_db().clients

all_clients = clients.find({'active': True, 'reseller': {'$ne': 1211590718}})
used = {}
for client in all_clients:
    if datetime.datetime.now().timestamp() > client['when']:
        continue
    if client['reseller'] not in used:
        used[client['reseller']] = client['traffic'] - client['usage']
    used[client['reseller']] += client['traffic'] - client['usage']
for key in used.keys():
    print(key)
    print(used[key])
    print('-------------')
# # client = clients.update_many({'active': True, 'pause': True, 'when': {'$gt': datetime.datetime.now().timestamp()}, '$expr': {'$gt': ['$traffic', '$usage']}}, {'$set':{'active': False, 'pause': True}})
# for c in clients.find({'active': False, 'pause': True, 'when': {'$gt': datetime.datetime.now().timestamp()}, '$expr': {'$gt': ['$traffic', '$usage']}}):
#     print(c)