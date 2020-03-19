# Bot's messages
from typing import List


"""
####################################################################
######################### GENERAL MESSAGES #########################
####################################################################
"""

def message_default_error():
    return "Brp"

def message_unexpected_error(command: str, *args):
    return f"An unexpected error while executing `!{command + (' ' if len(args) > 0 else '') + ' '.join(args)}`"

def message_group_not_exists_error(group: int) -> str:
    return f"Group {group} does not exist!"

def message_command_not_allowed() -> str:
    return "You are not allowed to execute this command"

def message_member_not_exists(member_name: str) -> str:
    return f"Member {member_name} does not exist!"

"""
####################################################################
######################### GROUP MESSAGES ###########################
####################################################################
"""

def message_group_created(category_name: str, group: int) -> str:
    return f"New **{category_name}** created! To join use the following command: `!join-group {group}`"

def message_group_deleted(category_name: str) -> str:
    return f"**{category_name}** deleted!"

def message_member_joined_group(member_name: str, group_name: str) -> str:
    return f"**{member_name} has joined to {group_name}!**"

def message_member_left_group(member_name: str, group_name: str) -> str:
    return f"**{member_name} has left {group_name}!**"

"""
####################################################################
######################### LIST MESSAGES ############################
####################################################################
"""

NUMBER_MAPPING = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
}

LETTER_EMOJI_PREFIX = "regional_indicator_"

def aux_map_number_to_emoji(number: int) -> str:
    return f":{NUMBER_MAPPING[number]}:"

def aux_map_letter_to_emoji(letter: str) -> str:
    return f":{LETTER_EMOJI_PREFIX}{letter}:"

def get_emoji_group(number: int, letter: str = 'g') -> str:
    L = [aux_map_number_to_emoji(int(digit)) for digit in list(str(number).split())]
    return f"{aux_map_letter_to_emoji(letter)} {' '.join(L)}"

def message_list_group_members(group: int, members: List) -> str:
    member_list = '\n - '.join([""] + [member.name for member in members])
    return f"{get_emoji_group(group)}`{member_list}`"

def message_no_members() -> str:
    return f"Nobody on this group"

def message_no_groups() -> str:
    return f"No groups created yet"