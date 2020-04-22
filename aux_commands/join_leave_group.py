import asyncio
from asyncio import Lock
from typing import Union, List

import discord

from aux_commands.open_close_groups import is_closed_group, open_group
from utils.guild_config import GUILD_CONFIG
from utils import helper_functions as hpf, bot_messages as btm

"""
####################################################################
##################### JOIN/LEAVE GROUP FUNCTIONS ###################
####################################################################
"""

invites_lock = Lock()


async def aux_join_group(
        ctx,
        member: discord.Member,
        group: Union[int, str],
        group_message: bool = True,
        general_message: bool = True
) -> bool:
    guild = ctx.guild
    new_role = hpf.get_lab_role(guild, group)
    new_lab_group = hpf.get_lab_group(guild, group)
    existing_lab_group = hpf.existing_member_lab_group(member)
    MAX_GROUP_SIZE = GUILD_CONFIG[guild]["MAX_STUDENTS_PER_GROUP"]
    if GUILD_CONFIG[guild]["REQUIRE_NICKNAME"] and not member.nick:
        await ctx.send(btm.message_member_need_name_error(member))
    elif existing_lab_group:
        await ctx.send(btm.error_member_already_in_group(hpf.get_nick(member), existing_lab_group.name))
    elif not new_role:
        await ctx.send(btm.message_lab_group_not_exists(new_lab_group.name))
    elif len(hpf.all_students_in_group(ctx, group)) >= MAX_GROUP_SIZE:
        await ctx.send(btm.message_max_members_in_group_error(new_lab_group.name, MAX_GROUP_SIZE))
    else:
        if not hpf.member_in_teaching_team(member, guild):
            group_num = hpf.get_lab_group_number(new_lab_group.name)
            async with invites_lock:
                invite_list = GUILD_CONFIG.group_invites(guild)
                invited = invite_list.has_invite(member.id, group_num)
                if is_closed_group(guild, new_lab_group) and not invited:
                    await ctx.send(btm.error_lab_group_is_closed(new_lab_group))
                    return False
                if invited:
                    invite_list.remove_invite(member.id, group_num)
                await member.add_roles(new_role)
        else:
            await member.add_roles(new_role)
        print(f'Role "{new_role}" assigned to {member}')
        # Move to voice channel if connected
        voice_channel = hpf.get_lab_voice_channel(guild, group)
        if voice_channel and member.voice and member.voice.channel:
            await member.move_to(voice_channel)
        # Message to group text channel
        text_channel = hpf.get_lab_text_channel(guild, group)
        if group_message and text_channel:
            await text_channel.send(btm.message_mention_member_when_join_group(member, new_lab_group.name))
        # Message to general channel
        general_text_channel = hpf.get_general_text_channel(guild)
        if general_message and general_text_channel and not hpf.member_in_teaching_team(member, guild):
            await general_text_channel.send(btm.message_member_joined_group(hpf.get_nick(member), new_lab_group.name))
        # Remove other invitations
        async with invites_lock:
            invite_list = GUILD_CONFIG.group_invites(guild)
            old_invites = invite_list.retrieve_invites(member.id)
            for group_invite in old_invites:
                text_channel = hpf.get_lab_text_channel(guild, group_invite)
                await text_channel.send(btm.info_member_accepted_another_invite(member))
        return True
    return False


async def aux_leave_group(
        ctx,
        member: discord.Member,
        group_message: bool = True,
        general_message: bool = True,
        show_open_message: bool = True,
        show_not_in_group_error: bool = True
):
    guild = ctx.guild
    existing_lab_role = hpf.existing_member_lab_role(member)
    if existing_lab_role:
        existing_lab_group = hpf.existing_member_lab_group(member)
        # Disconnect from the group voice channel if connected to it
        voice_channel = hpf.existing_member_lab_voice_channel(member)
        if voice_channel and member.voice and member.voice.channel == voice_channel:
            general_voice_channel = hpf.get_general_voice_channel(guild)
            # if no general_voice_channel, it will move user out of the current voice channel
            await member.move_to(general_voice_channel if hpf.member_in_teaching_team(member, guild) else None)
        # Message to group text channel
        text_channel = hpf.existing_member_lab_text_channel(member)
        if group_message and text_channel:
            await text_channel.send(btm.message_member_left_group(hpf.get_nick(member), existing_lab_group.name))
        # Remove group role
        await member.remove_roles(existing_lab_role)
        print(f'Role "{existing_lab_role}" removed to {member}')
        # Message to general channel
        general_text_channel = hpf.get_general_text_channel(guild)
        if general_message and general_text_channel and not hpf.member_in_teaching_team(member, guild):
            await general_text_channel.send(btm.message_member_left_group(hpf.get_nick(member), existing_lab_group.name))
        # If group get empty, open it
        if len(hpf.all_students_in_group(ctx, existing_lab_group.name)) < 1 and is_closed_group(guild, existing_lab_group):
            await open_group(guild, existing_lab_group)
            if show_open_message:
                await general_text_channel.send(btm.success_group_open(existing_lab_group))
    elif show_not_in_group_error:
        await ctx.send(btm.message_member_not_in_any_group(member))


async def aux_move_to(ctx, member: discord.Member, group: int):
    MAX_GROUP_SIZE = GUILD_CONFIG[ctx.guild]["MAX_STUDENTS_PER_GROUP"]
    if len(hpf.all_students_in_group(ctx, group)) >= MAX_GROUP_SIZE:
        await ctx.send(
            btm.message_max_members_in_group_error(hpf.get_lab_group_name(group), MAX_GROUP_SIZE))
    else:
        await aux_leave_group(ctx, member, show_not_in_group_error=False, general_message=False)
        await asyncio.sleep(1)
        if await aux_join_group(ctx, member, group, general_message=False):
            await ctx.send(btm.message_member_moved(member, hpf.get_lab_group_name(group)))


async def aux_invite_member(ctx, host_member: discord.Member, invited_member: discord.Member):
    guild = ctx.guild
    existing_lab_group = hpf.existing_member_lab_group(host_member)
    if not existing_lab_group:
        await ctx.send(btm.error_not_in_group_for_invite(host_member))
    elif hpf.member_in_teaching_team(invited_member, guild):
        await ctx.send(btm.error_can_not_invite_teaching_team())
    else:
        async with invites_lock:
            group_num = hpf.get_lab_group_number(existing_lab_group.name)
            invite_list = GUILD_CONFIG.group_invites(guild)
            if hpf.existing_member_lab_group(invited_member):
                await ctx.send(btm.error_member_already_in_group(invited_member.name, existing_lab_group.name))
            elif invite_list.has_invite(invited_member.id, group_num):
                await ctx.send(btm.error_invite_already_sent(invited_member))
            else:
                # Add invitation
                invite_list.add_invite(invited_member.id, group_num)
                general_text_channel = hpf.get_general_text_channel(guild)
                if general_text_channel:
                    await general_text_channel.send(
                        btm.success_invite_sent_to_group(invited_member, existing_lab_group, group_num))
                group_channel = hpf.get_lab_text_channel(guild, group_num)
                if group_channel:
                    await group_channel.send(btm.success_invite_sent(invited_member))
