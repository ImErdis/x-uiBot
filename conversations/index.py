"""
index.py
---------
index all function handlers
"""

# imports here -----------------------
from conversations import addserver, removeserver, createsubscription, generateacc, replaceserver

convs = [addserver.conv_handler,
         removeserver.conv_handler,
         createsubscription.conv_handler,
         generateacc.conv_handler,
         replaceserver.conv_handler]


# --------------------------------------
def conversations():
    """

    """
    return convs