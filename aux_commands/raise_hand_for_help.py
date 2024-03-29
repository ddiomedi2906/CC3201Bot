from asyncio import Lock
from typing import Union

import discord

from aux_commands.join_leave_group import aux_leave_group, aux_join_group, leave_group, join_group
from utils.emoji_utils import get_unicode_emoji_from_alias
from utils.guild_config import GUILD_CONFIG
from utils import helper_functions as hpf, bot_messages as btm

"""
####################################################################
##################### CALL-FOR-HELP FUNCTIONS #######################
####################################################################
"""

help_queue_lock = Lock()


async def go_for_help_from_message(member: discord.Member, message: discord.Message, group: Union[int, str]) -> bool:
    guild = member.guild
    if hpf.existing_member_lab_role(member):
        await leave_group(guild, member, hpf.existing_member_lab_role(member), hpf.existing_member_lab_group(member))
    lab_group = hpf.get_lab_group(guild, group)
    async with help_queue_lock:
        message_id = GUILD_CONFIG.help_queue(guild).extract_group(group)
    if not message_id:
        return False
    if message.channel:
        await message.channel.send(btm.info_on_the_way_to(member, lab_group.name))
    group_text_channel = hpf.get_lab_text_channel(guild, lab_group.name)
    if group_text_channel:
        await group_text_channel.send(btm.message_help_on_the_way(member, show_mention=True))
    if hpf.get_lab_role(guild, group):
        await join_group(guild, member, hpf.get_lab_role(guild, group), lab_group, group_message=False)
        return True
    return False


async def aux_go_for_help_from_command(ctx, member: discord.Member) -> bool:
    await aux_leave_group(ctx, member, show_not_in_group_error=False)
    # Get next group
    guild = member.guild
    async with help_queue_lock:
        group, message_id = GUILD_CONFIG.help_queue(guild).next()
    if not group:
        return False
    # If group found
    general_text_channel = hpf.get_general_text_channel(guild)
    try:
        message = await general_text_channel.fetch_message(message_id)
        await message.add_reaction(get_unicode_emoji_from_alias('thumbsup'))
    except discord.NotFound:
        pass
    if general_text_channel:
        await general_text_channel.send(btm.info_on_the_way_to(member, hpf.get_lab_group_name(group)))
    # Go for help
    group_text_channel = hpf.get_lab_text_channel(guild, group)
    if group_text_channel:
        await group_text_channel.send(btm.message_help_on_the_way(member, show_mention=True))
    await aux_join_group(ctx, member, group, group_message=False)
    return True


async def aux_raise_hand(ctx):
    member = ctx.author
    existing_lab_group = hpf.existing_member_lab_group(member)
    general_text_channel = hpf.get_general_text_channel(ctx.guild)
    if not existing_lab_group:
        await ctx.channel.send(btm.message_member_not_in_group_for_help())
    elif ctx.channel != hpf.existing_member_lab_text_channel(member):
        await ctx.channel.send(btm.error_stay_in_your_seat(ctx.author, existing_lab_group))
    elif general_text_channel:
        group_num = hpf.get_lab_group_number(existing_lab_group.name)
        # Check if group already asked for help
        async with help_queue_lock:
            help_queue = GUILD_CONFIG.help_queue(ctx.guild)
            queue_size = help_queue.size()
            if group_num in help_queue:
                await ctx.channel.send(btm.info_help_queue_size(queue_size - 1) if queue_size > 1 else ":eyes:")
                return
        # Get help
        online_team = hpf.all_teaching_team_members(ctx.author.guild)
        available_team = [member for member in online_team if not hpf.existing_member_lab_group(member)]
        help_message = None
        if available_team:
            await ctx.channel.send(btm.message_asking_for_help())
            help_message = await general_text_channel.send(
                btm.message_call_for_help(existing_lab_group.name, available_team))
        elif online_team:
            await ctx.channel.send(btm.message_no_one_available_error())
            help_message = await general_text_channel.send(
                btm.message_call_for_help(existing_lab_group.name, online_team))
        else:
            await ctx.channel.send(btm.message_no_one_online_error())
        if help_message:
            async with help_queue_lock:
                if queue_size > 0:
                    await ctx.channel.send(btm.info_help_queue_size(queue_size))
                help_queue.add(group=group_num, message_id=help_message.id)
    else:
        await ctx.channel.send(btm.message_can_not_get_help_error())
