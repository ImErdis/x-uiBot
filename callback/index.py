"""
index.py
---------
index all function handlers
"""

# imports here -----------------------
from callback import admin

command_map = {
    '^admin$': admin.admin,
    '^list_server$': admin.list_server,
    '^list_account$': admin.list_account,
    '^deleteserver_': admin.delete_server,
    '^edit_subscription$': admin.list_subscription,
    '^editsub_': admin.edit_subscription,
    '^changeserver_': admin.edit_subscription_servers,
    '^updatesub_': admin.update_subscription,
    '^listaccountsub_': admin.subscription_list_account,
    '^listaccount_': admin.control_account,
    '^controlaccountdelete_': admin.delete_account,
    '^server_': admin.control_server,

}


# --------------------------------------
def handlers():
    """

    """
    return command_map

