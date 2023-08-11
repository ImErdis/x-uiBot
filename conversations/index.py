"""
index.py
---------
index all function handlers
"""

# imports here -----------------------
from conversations import addserver, createsubscription, generateacc, replaceserver, creategroup, restoreaccount, \
    add_reseller, create_account, search_account, renew_account

convs = [addserver.conv_handler,
         createsubscription.conv_handler,
         generateacc.conv_handler,
         replaceserver.conv_handler,
         creategroup.conv_handler,
         restoreaccount.conv_handler,
         add_reseller.conv_handler,
         create_account.conv_handler,
         search_account.conv_handler,
         renew_account.conv_handler]


# --------------------------------------
def conversations():
    """

    """
    return convs