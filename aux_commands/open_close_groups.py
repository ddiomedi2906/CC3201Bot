import discord

from utils.guild_config import GUILD_CONFIG
import utils.helper_functions as hpf, utils.bot_messages as btm


async def is_open_group(guild: discord.Guild, group: discord.CategoryChannel) -> bool:
    return group.name in GUILD_CONFIG[guild]["OPEN_GROUPS"]


async def is_closed_group(guild: discord.Guild, group: discord.CategoryChannel) -> bool:
    return group.name in GUILD_CONFIG[guild]["CLOSED_GROUPS"]


async def aux_open_group(ctx, group: discord.CategoryChannel):
    guild = ctx.guild
    if not hpf.member_in_teaching_team(ctx.author, guild) or group != hpf.existing_member_lab_group(ctx.author):
        await ctx.send(btm.error_member_not_part_of_group(ctx.author, group))
    else:
        if is_closed_group(guild, group):
            GUILD_CONFIG[guild]["CLOSED_GROUPS"].remove(group.name)
        GUILD_CONFIG[guild]["OPEN_GROUPS"].add(group.name)
        print("OPEN_GROUPS", GUILD_CONFIG[guild]["OPEN_GROUPS"])
        print("CLOSED_GROUPS", GUILD_CONFIG[guild]["CLOSED_GROUPS"])


async def aux_close_group(ctx, group: discord.CategoryChannel):
    guild = ctx.guild
    if not hpf.member_in_teaching_team(ctx.author, guild) or group != hpf.existing_member_lab_group(ctx.author):
        await ctx.send(btm.error_member_not_part_of_group(ctx.author, group))
    else:
        if is_open_group(guild, group):
            GUILD_CONFIG[ctx.guild]["OPEN_GROUPS"].remove(group.name)
        GUILD_CONFIG[ctx.guild]["CLOSED_GROUPS"].add(group.name)
        print("OPEN_GROUPS", GUILD_CONFIG[ctx.guild]["OPEN_GROUPS"])
        print("CLOSED_GROUPS", GUILD_CONFIG[ctx.guild]["CLOSED_GROUPS"])
