import re
from typing import List

import discord

from global_variables import TT_ROLES, GENERAL_TEXT_CHANNEL_NAME
from utils import helper_functions as hpf, bot_messages as btm

"""
####################################################################
##################### CALL-FOR-HELP FUNCTIONS #######################
####################################################################
"""


def get_teaching_team_roles(guild: discord.Guild) -> List[discord.Role]:
    return [role for role in guild.roles if role.name in TT_ROLES]


def get_teaching_team_members(guild: discord.Guild) -> List[discord.Member]:
    tt_roles = get_teaching_team_roles(guild)
    available_team = []
    for role in tt_roles:
        available_team.extend(get_online_members_from_role(role))
    return available_team


def member_in_teaching_team(member: discord.Member, guild: discord.Guild) -> bool:
    tt_roles = get_teaching_team_roles(guild)
    for member_role in member.roles:
        if discord.utils.get(tt_roles, name=member_role.name):
            return True
    return False


def get_online_members_from_role(role: discord.Role) -> List[discord.Member]:
    return [member for member in role.members if member.status == discord.Status.online]


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


async def aux_raise_hand(ctx):
    member = ctx.author
    existing_lab_group = hpf.existing_member_lab_group(member)
    general_channel = discord.utils.get(member.guild.channels, name=GENERAL_TEXT_CHANNEL_NAME)
    if not existing_lab_group:
        await ctx.channel.send(btm.message_member_not_in_group_for_help())
    elif ctx.channel != hpf.existing_member_lab_text_channel(member):
        await ctx.channel.send(btm.message_stay_in_your_seat_error(ctx.author, existing_lab_group.name))
    elif general_channel:
        online_team = get_teaching_team_members(ctx.author.guild)
        available_team = [member for member in online_team if not hpf.existing_member_lab_group(member)]
        if available_team:
            await ctx.channel.send(btm.message_asking_for_help())
            await general_channel.send(btm.message_call_for_help(existing_lab_group.name, available_team))
        elif online_team:
            await ctx.channel.send(btm.message_no_one_available_error())
            await general_channel.send(btm.message_call_for_help(existing_lab_group.name, online_team))
        else:
            await ctx.channel.send(btm.message_no_one_online_error())
    else:
        await ctx.channel.send(btm.message_can_not_get_help_error())
