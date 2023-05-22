"""
index.py
---------
index all function handlers
"""

# imports here -----------------------
from conversations import addserver, createsubscription, generateacc, replaceserver, creategroup

convs = [addserver.conv_handler,
         createsubscription.conv_handler,
         generateacc.conv_handler,
         replaceserver.conv_handler,
         creategroup.conv_handler]


# --------------------------------------
def conversations():
    """

    """
    return convs