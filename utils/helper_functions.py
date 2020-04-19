import re
from typing import Union, Optional, List

import discord

from utils.guild_config import GUILD_CONFIG

"""
####################################################################
########################## HELP FUNCTIONS ##########################
####################################################################
"""

GROUP_NAME_PATTERN = re.compile("Group[\s]+([0-9]+)")
ROLE_NAME_PATTERN = re.compile("member-group\s+([0-9]+)")

def get_lab_group_number(group_name: str) -> Optional[int]:
    if GROUP_NAME_PATTERN.search(group_name):
        return int(GROUP_NAME_PATTERN.search(group_name).group(1))
    return None


def get_lab_group_name(number: int):
    return f"Group {number:2}"


def get_role_name(number: int):
    return f"member-group {number:2}"


def get_text_channel_name(number: int):
    return f"text-channel-{number}"


def get_voice_channel_name(number: int):
    return f"voice-channel {number}"


def get_nick(member: discord.Member) -> str:
    return member.nick if member.nick else member.name


def get_lab_group(guild: discord.Guild, group: Union[int, str]) -> Optional[discord.CategoryChannel]:
    name = get_lab_group_name(group) if type(group) == int else group
    return discord.utils.get(guild.categories, name=name)


def get_lab_role(guild: discord.Guild, group: Union[int, str]) -> Optional[discord.Role]:
    if type(group) == str and GROUP_NAME_PATTERN.search(group):
        group = int(GROUP_NAME_PATTERN.search(group).group(1))
    return discord.utils.get(guild.roles, name=get_role_name(group))


def get_lab_text_channel(guild: discord.Guild, group: Union[int, str]) -> Optional[discord.TextChannel]:
    if type(group) == str and GROUP_NAME_PATTERN.search(group):
        group = int(GROUP_NAME_PATTERN.search(group).group(1))
    return discord.utils.get(guild.channels, name=get_text_channel_name(group))


def get_lab_voice_channel(guild: discord.Guild, group: Union[int, str]) -> Optional[discord.VoiceChannel]:
    if type(group) == str and GROUP_NAME_PATTERN.search(group):
        group = int(GROUP_NAME_PATTERN.search(group).group(1))
    return discord.utils.get(guild.channels, name=get_voice_channel_name(group))


def all_existing_lab_roles(guild: discord.Guild) -> List[discord.Role]:
    return list(filter(lambda r: ROLE_NAME_PATTERN.search(r.name), guild.roles))


def all_existing_lab_groups(guild: discord.Guild) -> List[discord.CategoryChannel]:
    return [group for group in guild.categories if GROUP_NAME_PATTERN.search(group.name)]


def all_members_with_no_group(guild: discord.Guild) -> List[discord.Member]:
    return [member for member in guild.members if existing_member_lab_role(member) is None]


def all_non_empty_groups(guild: discord.Guild) -> List[discord.CategoryChannel]:
    student_role = discord.utils.get(guild.roles, name=GUILD_CONFIG[guild]["STUDENT_ROLE_NAME"])
    groups = set()
    for member in guild.members:
        if student_role in member.roles:
            existing_lab_group = existing_member_lab_group(member)
            if existing_lab_group:
                groups.add(existing_lab_group)
    return list(groups)


def all_empty_groups(guild: discord.Guild) -> List[discord.CategoryChannel]:
    all_groups = set(all_existing_lab_groups(guild))
    non_empty_groups = set(all_non_empty_groups(guild))
    return list(all_groups - non_empty_groups)


def all_students_in_group(ctx, group: Union[int, str]) -> List[discord.Member]:
    guild = ctx.guild
    existing_role = get_lab_role(guild, group)
    student_role = discord.utils.get(guild.roles, name=GUILD_CONFIG[guild]["STUDENT_ROLE_NAME"])
    if not existing_role:
        return []
    return [member for member in guild.members if existing_role in member.roles and student_role in member.roles]


def existing_group_number_from_role(role: discord.Role) -> Optional[int]:
    return int(ROLE_NAME_PATTERN.search(role.name).group(1)) if ROLE_NAME_PATTERN.search(role.name) else None


def existing_group_number(member: discord.Member) -> Optional[int]:
    member_roles = member.roles
    for role in member_roles:
        group = existing_group_number_from_role(role)
        if group:
            return group
    return None


def existing_member_lab_role(member: discord.Member) -> Optional[discord.Role]:
    member_roles = member.roles
    for role in member_roles:
        if ROLE_NAME_PATTERN.search(role.name):
            return role
    return None


def existing_member_lab_group(member: discord.Member) -> Optional[discord.CategoryChannel]:
    member_roles = member.roles
    for role in member_roles:
        if ROLE_NAME_PATTERN.search(role.name):
            num = int(ROLE_NAME_PATTERN.search(role.name).group(1))
            return discord.utils.get(member.guild.categories, name=get_lab_group_name(num))
    return None


def existing_member_lab_text_channel(member: discord.Member) -> Optional[discord.TextChannel]:
    member_roles = member.roles
    for role in member_roles:
        if ROLE_NAME_PATTERN.search(role.name):
            num = int(ROLE_NAME_PATTERN.search(role.name).group(1))
            return discord.utils.get(member.guild.channels, name=get_text_channel_name(num))
    return None


def existing_member_lab_voice_channel(member: discord.Member) -> Optional[discord.VoiceChannel]:
    member_roles = member.roles
    for role in member_roles:
        if ROLE_NAME_PATTERN.search(role.name):
            num = int(ROLE_NAME_PATTERN.search(role.name).group(1))
            return discord.utils.get(member.guild.channels, name=get_voice_channel_name(num))
    return None
