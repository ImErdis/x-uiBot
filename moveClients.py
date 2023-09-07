from configuration import Config

config = Config('configuration.yaml')
config.show_label()

svs = config.get_db().servers
subs = config.get_db().subscriptions
groups = config.get_db().groups
clients = config.get_db().clients

all_clients = clients.find({'active': True})
used = [x['traffic'] - x['usage'] for x in all_clients]
print(sum(used))

