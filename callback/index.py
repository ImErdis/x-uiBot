"""
index.py
---------
index all function handlers
"""

# imports here -----------------------
from callback import admin, public, toggle_reseller

command_map = {
    '^admin$': admin.admin,
    '^list_server$': admin.list_server,
    '^list_account$': admin.list_account,
    '^deleteserver_': admin.delete_server,
    # '^edit_subscription$': admin.list_subscription,
    # '^editsub_': admin.edit_subscription,
    # '^changeserver_': admin.edit_subscription_servers,
    # '^updatesub_': admin.update_subscription,
    '^listaccountsub_': admin.subscription_list_account,
    '^listaccountgroup_': admin.group_list_account,
    '^listaccount_': admin.control_account,
    '^controlaccountdelete_': admin.delete_account,
    '^server_': admin.control_server,
    '^accounts_reseller_': admin.accounts_reseller,
    '^information_reseller$': admin.information_reseller,
    '^contact-info$': public.contact,
    '^account-info_': admin.account_reseller,
    '^list_reseller_': admin.list_resellers,
    '^reseller_': admin.reseller_control,
    '^disable_reseller_': toggle_reseller.disable_reseller,
    '^enable_reseller_': toggle_reseller.enable_reseller

}


# --------------------------------------
def handlers():
    """

    """
    return command_map

