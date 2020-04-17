import re
from typing import List

import discord

from utils import helper_functions as hpf, bot_messages as btm

"""
####################################################################
##################### CALL-FOR-HELP FUNCTIONS #######################
####################################################################
"""

def get_teaching_team_roles(guild: discord.Guild, TT_role_names: List[str]) -> List[discord.Role]:
    return list(filter(lambda r: r.name in TT_role_names, guild.roles))


def get_teaching_team_members(guild: discord.Guild, TT_role_names: List[str]) -> List[discord.Member]:
    TT_roles = get_teaching_team_roles(guild, TT_role_names)
    available_team = []
    for role in TT_roles:
        available_team.extend(get_available_members_from_role(role))
    return available_team


def member_in_teaching_team(member: discord.Member, guild: discord.Guild, TT_role_names: List[str]) -> bool:
    TT_roles = get_teaching_team_roles(guild, TT_role_names)
    for member_role in member.roles:
        if discord.utils.get(TT_roles, name=member_role.name):
            return True
    return False

def get_available_members_from_role(role: discord.Role) -> List[discord.Member]:
    if not role:
        return []
    online_role_members = [member for member in role.members if member.status == discord.Status.online]
    available_members = []
    for member in online_role_members:
        member_roles = member.roles
        available = True
        for role in member_roles:
            if re.search("member-group\s+[0-9]+", role.name):
                available = False
                break
        if available:
            available_members.append(member)
    return available_members


async def go_for_help(member: discord.Member, lab_group: discord.CategoryChannel, group: int):
    text_channel_name = hpf.get_text_channel_name(group)
    text_channel = discord.utils.get(lab_group.channels, name=text_channel_name)
    if text_channel:
        await text_channel.send(btm.message_help_on_the_way(member))
    voice_channel_name = hpf.get_voice_channel_name(group)
    voice_channel = discord.utils.get(lab_group.channels, name=voice_channel_name)
    if voice_channel and member.voice and member.voice.channel:
        await member.move_to(voice_channel)
    lab_group_role = hpf.get_lab_role(lab_group.guild, lab_group.name)
    if lab_group_role:
        await member.add_roles(lab_group_role)