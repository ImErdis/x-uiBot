from configuration import Config

config = Config('configuration.yaml')
config.show_label()

svs = config.get_db().servers
subs = config.get_db().subscriptions
groups = config.get_db().groups
clients = config.get_db().clients

result = clients.count_documents({f'servers.6467cd45ad9f9869c107aa2e': {'$exists': 1}})
print(result)

