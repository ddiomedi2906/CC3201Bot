from typing import Union, List

import discord

from aux_commands.open_close_groups import close_group
from utils.guild_config import GUILD_CONFIG
from utils import helper_functions as hpf, bot_messages as btm

"""
####################################################################
##################### JOIN/LEAVE GROUP FUNCTIONS ###################
####################################################################
"""


async def aux_join_group(ctx, member: discord.Member, group: Union[int, str]) -> bool:
    guild = ctx.guild
    new_role = hpf.get_lab_role(guild, group)
    new_lab_group_name = hpf.get_lab_group_name(group) if type(group) == int else group
    existing_lab_group = hpf.existing_member_lab_group(member)
    MAX_GROUP_SIZE = GUILD_CONFIG[guild]["MAX_STUDENTS_PER_GROUP"]
    if GUILD_CONFIG[guild]["REQUIRE_NICKNAME"] and not member.nick:
        await ctx.send(btm.message_member_need_name_error(member))
    elif existing_lab_group:
        await ctx.send(btm.message_member_already_in_group(hpf.get_nick(member), existing_lab_group.name))
    elif not new_role:
        await ctx.send(btm.message_lab_group_not_exists(new_lab_group_name))
    elif len(hpf.all_students_in_group(ctx, group)) >= MAX_GROUP_SIZE:
        await ctx.send(btm.message_max_members_in_group_error(new_lab_group_name, MAX_GROUP_SIZE))
    else:
        await member.add_roles(new_role)
        print(f'Role "{new_role}" assigned to {member}')
        # Move to voice channel if connected
        voice_channel = discord.utils.get(guild.voice_channels,
                                          name=hpf.get_lab_voice_channel(guild, group))
        if voice_channel and member.voice and member.voice.channel:
            await member.move_to(voice_channel)
        # Message to group text channel
        text_channel = discord.utils.get(guild.text_channels,
                                         name=hpf.get_lab_text_channel(guild, group))
        if text_channel:
            await text_channel.send(btm.message_mention_member_when_join_group(member, new_lab_group_name))
        # Message to general channel
        general_text_channel = discord.utils.get(guild.text_channels,
                                                 name=GUILD_CONFIG[guild]["GENERAL_TEXT_CHANNEL_NAME"])
        if general_text_channel and not hpf.member_in_teaching_team(member, guild):
            await general_text_channel.send(btm.message_member_joined_group(hpf.get_nick(member), new_lab_group_name))
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
            general_voice_channel = discord.utils.get(guild.voice_channels,
                                                      name=GUILD_CONFIG[guild]["GENERAL_VOICE_CHANNEL_NAME"])
            # if no general_voice_channel, it will move user out of the current voice channel
            await member.move_to(general_voice_channel if hpf.member_in_teaching_team(member, guild) else None)
        # Message to group text channel
        text_channel = hpf.existing_member_lab_text_channel(member)
        if text_channel:
            await text_channel.send(btm.message_member_left_group(hpf.get_nick(member), existing_lab_group.name))
        await member.remove_roles(existing_lab_role)
        print(f'Role "{existing_lab_role}" removed to {member}')
        # Message to general channel
        general_text_channel = discord.utils.get(guild.text_channels,
                                                 name=GUILD_CONFIG[guild]["GENERAL_TEXT_CHANNEL_NAME"])
        if general_text_channel and not hpf.member_in_teaching_team(member, guild):
            await general_text_channel.send(btm.message_member_left_group(hpf.get_nick(member), existing_lab_group.name))
        if hpf.all_students_in_group(ctx, existing_lab_group.name) < 1:
            await close_group(guild, existing_lab_group)
    elif show_not_in_group_error:
        await ctx.send(btm.message_member_not_in_any_group(hpf.get_nick(member)))


async def aux_move_to(ctx, member: discord.Member, group: int):
    MAX_GROUP_SIZE = GUILD_CONFIG[ctx.guild]["MAX_STUDENTS_PER_GROUP"]
    if len(hpf.all_students_in_group(ctx, group)) >= MAX_GROUP_SIZE:
        await ctx.send(
            btm.message_max_members_in_group_error(hpf.get_lab_group_name(group), MAX_GROUP_SIZE))
    else:
        await aux_leave_group(ctx, member, show_not_in_group_error=False)
        await aux_join_group(ctx, member, group)