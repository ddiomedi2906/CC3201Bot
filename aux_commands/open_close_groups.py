from asyncio import Lock
from typing import List

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


async def aux_open_group(ctx, group: discord.CategoryChannel):
    guild = ctx.guild
    if not (hpf.member_in_teaching_team(ctx.author, guild) or group == hpf.existing_member_lab_group(ctx.author)):
        await ctx.send(btm.error_member_not_part_of_group(ctx.author, group))
    else:
        await open_group(guild, group)
        general_text_channel = hpf.get_general_text_channel(guild)
        if general_text_channel:
            await general_text_channel.send(btm.success_group_open(group))
        print("OPEN_GROUPS", GUILD_CONFIG[guild]["OPEN_GROUPS"])
        print("CLOSED_GROUPS", GUILD_CONFIG[guild]["CLOSED_GROUPS"])


async def aux_close_group(ctx, group: discord.CategoryChannel):
    guild = ctx.guild
    if not (hpf.member_in_teaching_team(ctx.author, guild) or group == hpf.existing_member_lab_group(ctx.author)):
        await ctx.send(btm.error_member_not_part_of_group(ctx.author, group))
    else:
        await close_group(guild, group)
        general_text_channel = hpf.get_general_text_channel(guild)
        if general_text_channel:
            await general_text_channel.send(btm.success_group_closed(group))
        print("OPEN_GROUPS", GUILD_CONFIG[ctx.guild]["OPEN_GROUPS"])
        print("CLOSED_GROUPS", GUILD_CONFIG[ctx.guild]["CLOSED_GROUPS"])
