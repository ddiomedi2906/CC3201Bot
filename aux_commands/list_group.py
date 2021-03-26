import re
from typing import Optional

import discord

from aux_commands.open_close_groups import is_open_group, is_closed_group
from utils import helper_functions as hpf, bot_messages as btm


def aux_group_details(
        ctx,
        group: discord.CategoryChannel,
        details: bool = False,
        none_if_empty: bool = False,
        only_online = False
) -> Optional[str]:
    guild = ctx.guild
    members = hpf.all_students_in_group(guild, group.name)
    if only_online:
        members = hpf.select_online_members(guild, members)
    if not members and none_if_empty:
        return None
    if details:
        return btm.info_group_details(members, group, is_open=is_open_group(guild, group))
    else:
        return btm.message_list_group_members(hpf.get_lab_group_number(group.name), members)


async def aux_get_list(ctx, message_size: int = 200, only_open_groups: bool = False, exclude_empty: bool = True, exclude_no_group: bool = False, only_online = False):
    existing_lab_groups = hpf.all_existing_lab_groups(ctx.guild)

    if not existing_lab_groups:
        await ctx.send(btm.info_no_groups())
    else:
        message_list = []
        message_acc = "**List**"
        if only_open_groups or exclude_empty or exclude_no_group or only_online:
            message_acc += " **[Excluding:"
            if only_open_groups:
                message_acc += " closed-groups"
            if exclude_empty:
                message_acc += " empty-groups"
            if exclude_no_group:
                message_acc += " no-group"
            if only_online:
                message_acc += " not-online"
            message_acc += "]**"
        for lab_group in sorted(existing_lab_groups, key=lambda g: g.name):
            if only_open_groups and is_closed_group(ctx.guild, lab_group):
                continue
            message = aux_group_details(ctx, lab_group, details=True, none_if_empty=exclude_empty, only_online=only_online)
            if message and len(message_acc) + len(message) < message_size:
                message_acc += '\n' + message
            elif message:
                message_list.append(message_acc)
                message_acc = '...\n' + message
        if not exclude_no_group:
            members_no_group = hpf.all_students_with_no_group(ctx.guild)
            if members_no_group:
                if only_online:
                    members_no_group = hpf.select_online_members(ctx.guild, members_no_group)
                if members_no_group:
                    message = btm.message_list_no_group_members(members_no_group)
                    if message and len(message_acc) + len(message) < message_size:
                        message_acc += '\n' + message
                    elif message:
                        message_list.append(message_acc)
                        message_acc = '...\n' + message
        message_list.append(message_acc)
        if existing_lab_groups:
            for message in message_list:
                await ctx.send(message)