"""
index.py
---------
index all function handlers
"""


# imports here -----------------------
from .start import start, remaining

command_map = {
    'start': start,
    'remaining': remaining
    }

# --------------------------------------
def index():
    """
    
    """
    return command_map