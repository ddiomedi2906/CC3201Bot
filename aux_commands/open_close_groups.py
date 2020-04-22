from asyncio import Lock
from typing import List, Optional

import discord

from utils.guild_config import GUILD_CONFIG
import utils.helper_functions as hpf, utils.bot_messages as btm

open_close_lock = Lock()

def is_open_group(guild: discord.Guild, group: discord.CategoryChannel) -> bool:
    return group.name in GUILD_CONFIG[guild]["OPEN_GROUPS"]


def is_closed_group(guild: discord.Guild, group: discord.CategoryChannel) -> bool:
    return group.name in GUILD_CONFIG[guild]["CLOSED_GROUPS"]


def all_open_groups(guild: discord.Guild) -> List[discord.CategoryChannel]:
    return [group for group in hpf.all_existing_lab_groups(guild) if is_open_group(guild, group)]


def all_closed_groups(guild: discord.Guild) -> List[discord.CategoryChannel]:
    return [group for group in hpf.all_existing_lab_groups(guild) if is_closed_group(guild, group)]


async def open_group(guild: discord.Guild, group: discord.CategoryChannel):
    async with open_close_lock:
        if is_closed_group(guild, group):
            GUILD_CONFIG[guild]["CLOSED_GROUPS"].remove(group.name)
        GUILD_CONFIG[guild]["OPEN_GROUPS"].add(group.name)
    text_channel = hpf.get_lab_text_channel(guild, group.name)
    if text_channel:
        await text_channel.send(btm.success_group_open(group))


async def close_group(guild: discord.Guild, group: discord.CategoryChannel):
    async with open_close_lock:
        if is_open_group(guild, group):
            GUILD_CONFIG[guild]["OPEN_GROUPS"].remove(group.name)
        GUILD_CONFIG[guild]["CLOSED_GROUPS"].add(group.name)
    text_channel = hpf.get_lab_text_channel(guild, group.name)
    if text_channel:
        await text_channel.send(btm.success_group_closed(group))


async def aux_remove_group(guild: discord.Guild, group: discord.CategoryChannel):
    async with open_close_lock:
        if is_closed_group(guild, group):
            GUILD_CONFIG[guild]["CLOSED_GROUPS"].remove(group.name)
        if is_open_group(guild, group):
            GUILD_CONFIG[guild]["OPEN_GROUPS"].remove(group.name)


async def aux_open_group(ctx, group: Optional[discord.CategoryChannel]):
    guild = ctx.guild
    member_group = hpf.existing_member_lab_group(ctx.author)
    is_in_teaching_team = hpf.member_in_teaching_team(ctx.author, guild)
    if not member_group and not is_in_teaching_team:
        await ctx.send(btm.message_member_not_in_any_group(ctx.author))
    elif group and (not (is_in_teaching_team or group == member_group)):
        await ctx.send(btm.error_member_not_part_of_group(ctx.author, group if group else member_group))
    else:
        group_to_be_open = group if group else member_group
        await open_group(guild, group_to_be_open)
        general_text_channel = hpf.get_general_text_channel(guild)
        if general_text_channel:
            await general_text_channel.send(btm.success_group_open(group_to_be_open))
        print("OPEN_GROUPS", GUILD_CONFIG[guild]["OPEN_GROUPS"])
        print("CLOSED_GROUPS", GUILD_CONFIG[guild]["CLOSED_GROUPS"])


async def aux_close_group(ctx, group: Optional[discord.CategoryChannel]):
    guild = ctx.guild
    member_group = hpf.existing_member_lab_group(ctx.author)
    is_in_teaching_team = hpf.member_in_teaching_team(ctx.author, guild)
    if not member_group and not is_in_teaching_team:
        await ctx.send(btm.message_member_not_in_any_group(ctx.author))
    elif group and (not (is_in_teaching_team or group == member_group)):
        await ctx.send(btm.error_member_not_part_of_group(ctx.author, group if group else member_group))
    else:
        group_to_be_closed = group if group else member_group
        await close_group(guild, group_to_be_closed)
        general_text_channel = hpf.get_general_text_channel(guild)
        if general_text_channel:
            await general_text_channel.send(btm.success_group_closed(group_to_be_closed))
        print("OPEN_GROUPS", GUILD_CONFIG[ctx.guild]["OPEN_GROUPS"])
        print("CLOSED_GROUPS", GUILD_CONFIG[ctx.guild]["CLOSED_GROUPS"])
