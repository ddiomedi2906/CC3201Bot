
# Bot's messages

A = 1

"""
####################################################################
######################### GENERAL MESSAGES #########################
####################################################################
"""

def message_default_error():
    return "Brp"

def message_unexpected_error(command, *args):
    return f"An unexpected error while executing `!{command + (' ' if len(args) > 0 else '') + ' '.join(args)}` :()"

"""
####################################################################
######################### GROUP MESSAGES ###########################
####################################################################
"""

def message_group_created(category_name: str, group: int) -> str:
    return f"New **{category_name}** created! To join use the following command: `!join-group {group}`"

def message_group_deleted(category_name: str) -> str:
    return f"**{category_name}** deleted!"