"""
index.py
---------
index all function handlers
"""

# imports here -----------------------
from conversations import addserver, createsubscription, generateacc, replaceserver, creategroup, restoreaccount

convs = [addserver.conv_handler,
         createsubscription.conv_handler,
         generateacc.conv_handler,
         replaceserver.conv_handler,
         creategroup.conv_handler,
         restoreaccount.conv_handler]


# --------------------------------------
def conversations():
    """

    """
    return convs