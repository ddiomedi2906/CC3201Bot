# Bot's messages
from typing import List

import discord

"""
####################################################################
######################### GENERAL MESSAGES #########################
####################################################################
"""

def message_default_error():
    return "Brp"

def message_unexpected_error(command: str, *args):
    return f"An unexpected error while executing `!{command + (' ' if len(args) > 0 else '') + ' '.join(args)}`"

def message_group_not_exists_error(group: str) -> str:
    return f"**{group}** does not exist!"

def message_command_not_allowed() -> str:
    return "You are not allowed to execute this command"

def message_member_not_exists(member_name: str) -> str:
    return f"Member **{member_name}** does not exist!"

def message_lab_group_not_exists(group_name: str) -> str:
    return f"**{group_name}** does not exist!"

"""
####################################################################
######################### GROUP MESSAGES ###########################
####################################################################
"""

def message_group_created(category_name: str, group: int) -> str:
    return f"New **{category_name}** created! To join use the following command: `!labgroup join {group}`"

def message_group_deleted(category_name: str) -> str:
    return f"**{category_name}** deleted!"

def message_member_joined_group(member_name: str, group_name: str) -> str:
    return f"**{member_name}** has joined to **{group_name}!**"

def message_mention_member_when_join_group(member: discord.Member, group_name: str) -> str:
    return f"**{member.mention}** has joined to **{group_name}!**"

def message_member_already_in_group(member_name: str, group_name: str) -> str:
    return f"**{member_name}** is already part of **{group_name}!**"

def message_max_members_in_group_error(group_name: str, max_size: int) -> str:
    return f"**{group_name}!** has reached its maximum limit! (**{max_size}**)"

def message_member_left_group(member_name: str, group_name: str) -> str:
    return f"**{member_name}** has left **{group_name}!**"

def message_member_not_in_group(member_name: str) -> str:
    return f"**{member_name}** is not part group!"

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
    # L = [aux_map_number_to_emoji(int(digit)) for digit in list(str(number).split())]
    L = []
    while number >= 10:
        L.append(aux_map_number_to_emoji(number%10))
        number //= 10
    L.append(aux_map_number_to_emoji(number))
    L.reverse()
    return f"{aux_map_letter_to_emoji(letter)} {' '.join(L)}"

def message_list_group_members(group: int, members: List) -> str:
    member_list = '\n - '.join([""] + [member.name for member in members])
    return f"{get_emoji_group(group)}`{member_list}`"

def message_no_members() -> str:
    return f"Nobody on this group"

def message_no_groups() -> str:
    return f"No groups created yet"

"""
####################################################################
######################### HELP MESSAGES ############################
####################################################################
"""

def message_call_for_help(group_name: str, available_members: List[discord.Member]) -> str:
    members_string = ' '.join([member.mention for member in available_members]) if available_members else "Nobody available :("
    return f"**{group_name}** is calling for help. \n {members_string}"

def message_help_on_the_way(member: discord.Member, show_mention: bool = False) -> str:
    return f"**{member.mention if show_mention else member.name}** on the way!"

def message_member_not_in_group_for_help() -> str:
    return f"You have to be part of a group to raise your hand. Try using `!labgroup join <number>` :)"

def message_asking_for_help() -> str:
    return f"Sure, I will bring someone."

def message_no_one_available_error() -> str:
    return f"Hey! No one is available for the moment. Please stay on the line :)"

def message_no_one_online_error() -> str:
    return f"No one is online :("

def message_can_not_get_help_error() -> str:
    return "Sorry, I can't do that right now."

def message_stay_in_your_seat_error(member: discord.Member, group_name: str) -> str:
    return f"Please {member.mention} stay in your group! (**{group_name}**)"