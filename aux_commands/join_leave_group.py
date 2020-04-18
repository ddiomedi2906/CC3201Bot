from typing import Union, List

import discord

from global_variables import STUDENT_ROLE_NAME, GENERAL_TEXT_CHANNEL_NAME, MAX_STUDENTS_PER_GROUP
from utils import helper_functions as hpf, bot_messages as btm
from utils.helper_functions import get_nick
from aux_commands.raise_hand_for_help import member_in_teaching_team

"""
####################################################################
##################### JOIN/LEAVE GROUP FUNCTIONS ###################
####################################################################
"""

def get_students_in_group(ctx, group: Union[int, str]) -> List[discord.Member]:
    guild = ctx.guild
    existing_role = hpf.get_lab_role(guild, group)
    student_role = discord.utils.get(guild.roles, name=STUDENT_ROLE_NAME)
    if not existing_role:
        return []
    return [member for member in guild.members if existing_role in member.roles and student_role in member.roles]


async def aux_join_group(ctx, member: discord.Member, group: Union[int, str]):
    guild = ctx.guild
    new_role = hpf.get_lab_role(guild, group)
    new_lab_group_name = hpf.get_lab_group_name(group) if type(group) == int else group
    existing_lab_group = hpf.existing_member_lab_group(member)
    if not member.nick:
        await ctx.send(btm.message_member_need_name_error(member))
    elif existing_lab_group:
        await ctx.send(btm.message_member_already_in_group(get_nick(member), existing_lab_group.name))
    elif not new_role:
        await ctx.send(btm.message_lab_group_not_exists(new_lab_group_name))
    elif len(get_students_in_group(ctx, group)) >= MAX_STUDENTS_PER_GROUP:
        await ctx.send(btm.message_max_members_in_group_error(new_lab_group_name, MAX_STUDENTS_PER_GROUP))
    else:
        await member.add_roles(new_role)
        print(f'Role "{new_role}" assigned to {member}')
        # Move to voice channel if connected
        voice_channel = discord.utils.get(guild.channels,
                                          name=hpf.get_voice_channel_name(group) if type(group) == int else group)
        if voice_channel and member.voice and member.voice.channel:
            await member.move_to(voice_channel)
        # Message to group text channel
        text_channel = discord.utils.get(guild.channels,
                                         name=hpf.get_text_channel_name(group) if type(group) == int else group)
        if text_channel:
            await text_channel.send(btm.message_mention_member_when_join_group(member, new_lab_group_name))
        # Message to general channel
        general_channel = discord.utils.get(guild.channels, name=GENERAL_TEXT_CHANNEL_NAME)
        if general_channel and not member_in_teaching_team(member, guild):
            await general_channel.send(btm.message_member_joined_group(get_nick(member), new_lab_group_name))
        return True
    return False


async def aux_leave_group(ctx, member: discord.Member, show_not_in_group_error: bool = True):
    guild = ctx.guild
    existing_lab_role = hpf.existing_member_lab_role(member)
    if existing_lab_role:
        existing_lab_group = hpf.existing_member_lab_group(member)
        # Disconnect from the group voice channel if connected to it
        voice_channel = hpf.existing_member_lab_voice_channel(member)
        if voice_channel and member.voice and member.voice.channel == voice_channel:
            await member.move_to(None)
        # Message to group text channel
        text_channel = hpf.existing_member_lab_text_channel(member)
        if text_channel:
            await text_channel.send(btm.message_member_left_group(get_nick(member), existing_lab_group.name))
        await member.remove_roles(existing_lab_role)
        print(f'Role "{existing_lab_role}" removed to {member}')
        # Message to general channel
        general_channel = discord.utils.get(guild.channels, name=GENERAL_TEXT_CHANNEL_NAME)
        if general_channel and not member_in_teaching_team(member, guild):
            await general_channel.send(btm.message_member_left_group(get_nick(member), existing_lab_group.name))
    elif show_not_in_group_error:
        await ctx.send(btm.message_member_not_in_group(get_nick(member)))


async def aux_move_to(ctx, member_mention: discord.Member, group: int):
    member = discord.utils.get(ctx.message.mentions, name=member_mention.name)
    if not member:
        await ctx.send(btm.message_member_not_exists(member_mention.nick))
    elif len(get_students_in_group(ctx, group)) >= MAX_STUDENTS_PER_GROUP:
        await ctx.send(
            btm.message_max_members_in_group_error(hpf.get_lab_group_name(group) if type(group) == int else group,
                                                   MAX_STUDENTS_PER_GROUP))
    else:
        await aux_leave_group(ctx, member, show_not_in_group_error=False)
        await aux_join_group(ctx, member, group)