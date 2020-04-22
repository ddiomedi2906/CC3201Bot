from typing import List, Optional

import discord

from utils.emoji_utils import get_unicode_emoji_from_alias
from utils import bot_messages as btm, helper_functions as hpf


async def aux_broadcast(ctx, message: str):
    guild = ctx.guild
    general_text_channel = hpf.get_general_text_channel(guild)
    if general_text_channel:
        await general_text_channel.send(btm.broadcast_message_from(ctx.author, message))
    for group in hpf.all_existing_lab_groups(guild):
        text_channel = hpf.get_lab_text_channel(guild, group.name)
        await text_channel.send(btm.broadcast_message_from(ctx.author, message))


async def aux_whereis(ctx, members: List[discord.Member], invalid_name: Optional[str] = None):
    if invalid_name:
        await ctx.send(btm.message_member_not_exists(invalid_name))
    for member in members:
        lab_group = hpf.existing_member_lab_group(member)
        if lab_group:
            await ctx.send(btm.message_where_is_member(member, lab_group))
        else:
            await ctx.send(btm.message_member_not_in_any_group(hpf.get_nick(member)))


async def aux_salute(author: discord.Member, text_channel: Optional[discord.TextChannel] = None):
    guild = author.guild
    author = author
    if text_channel:
        await text_channel.send(get_unicode_emoji_from_alias('wave'))
    await author.create_dm()
    if author.nick:
        await author.dm_channel.send(btm.info_welcome_to_guild(author, guild))
    else:
        await author.dm_channel.send(btm.error_member_need_name_in_guild(author, guild))