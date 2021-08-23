from asyncio import Lock
from typing import Union

import discord

from aux_commands.log_update import update_tt_members_log
from aux_commands.join_leave_group import aux_leave_group, aux_join_group, leave_group, join_group
from utils.emoji_utils import get_unicode_emoji_from_alias
from utils.guild_config import GUILD_CONFIG
from utils import helper_functions as hpf, bot_messages as btm

"""
#####################################################################
###################### CALL-FOR-HELP FUNCTIONS ######################
#####################################################################
"""

help_queue_lock = Lock()


async def go_for_help_from_message(member: discord.Member, message: discord.Message, group: Union[int, str]) -> bool:
    guild = member.guild
    online_team = hpf.all_teaching_team_members(guild)
    available_team = [members for members in online_team if not hpf.existing_member_lab_group(member)]
    help_message = None
    if hpf.existing_member_lab_role(member):
        await leave_group(guild, member, hpf.existing_member_lab_role(member), hpf.existing_member_lab_group(member))
    lab_group = hpf.get_lab_group(guild, group)
    async with help_queue_lock:
        message_id = GUILD_CONFIG.help_queue(guild).extract_group(group)
    help_queue = GUILD_CONFIG.help_queue(guild)
    queue_size = help_queue.size()
    queue_keys = list(help_queue.map_group_to_message_id.keys())
    if not message_id:
        return False
    log_text_channel = hpf.get_log_text_channel(guild)
    private_text_channel = hpf.get_private_text_channel(guild)
    if log_text_channel:
        await update_tt_members_log(message, member, lab_group)
    group_text_channel = hpf.get_lab_text_channel(guild, lab_group.name)
    if group_text_channel:
        await group_text_channel.send(btm.message_help_on_the_way(member, show_mention=True))
    if hpf.get_lab_role(guild, group):
        await join_group(guild, member, hpf.get_lab_role(guild, group), lab_group, group_message=False)
        # Update message
        if available_team:
            help_message = await private_text_channel.send(
                btm.message_call_for_help(hpf.get_queue_groups_names(queue_keys), available_team))
        elif online_team:
            help_message = await private_text_channel.send(
                btm.message_call_for_help(hpf.get_queue_groups_names(queue_keys), online_team))

        if queue_size > 0:
            prev_message = help_queue.map_group_to_message_id.get(list(help_queue.map_group_to_message_id)[-1])
            help_queue.map_group_to_message_id[int(list(help_queue.map_group_to_message_id)[-1])] = help_message.id
            supr = await private_text_channel.fetch_message(prev_message)
            await supr.delete(delay = 0)
        else:
            empty_queue_message = await private_text_channel.send(
                btm.queue_is_empty_message(), delete_after= 10)
            help_queue.empty_queue_message = empty_queue_message.id
            supr1 = await private_text_channel.fetch_message(message_id)
            supr2 = await private_text_channel.fetch_message(help_message.id)
            await supr1.delete(delay = 0)
            await supr2.delete(delay = 0)
        return True
    return False


async def aux_go_for_help_from_command(ctx, member: discord.Member) -> bool:
    
    online_team = hpf.all_teaching_team_members(ctx.author.guild)
    available_team = [member for member in online_team if not hpf.existing_member_lab_group(member)]
    help_message = None
    await aux_leave_group(ctx, member, show_not_in_group_error=False)
    # Get next group
    guild = member.guild
    async with help_queue_lock:
        group, message_id = GUILD_CONFIG.help_queue(guild).next()
    if not group:
        return False
    help_queue = GUILD_CONFIG.help_queue(ctx.guild)
    queue_size = help_queue.size()
    queue_keys = list(help_queue.map_group_to_message_id.keys())
    # If group found
    private_text_channel = hpf.get_private_text_channel(ctx.guild)
    log_text_channel = hpf.get_log_text_channel(ctx.guild)
    try:
        message = await private_text_channel.fetch_message(message_id)
        await message.add_reaction(get_unicode_emoji_from_alias('thumbsup'))
    except discord.NotFound:
        pass
    lab_group = hpf.get_lab_group(guild, group)
    if log_text_channel:
        await update_tt_members_log(ctx, ctx.author, lab_group)
    # Go for help
    group_text_channel = hpf.get_lab_text_channel(guild, group)
    if group_text_channel:
        await group_text_channel.send(btm.message_help_on_the_way(member, show_mention=True))
    await aux_join_group(ctx, member, group, group_message=False)

    # Update message
    if available_team:
        help_message = await private_text_channel.send(
            btm.message_call_for_help(hpf.get_queue_groups_names(queue_keys), available_team))
    elif online_team:
        help_message = await private_text_channel.send(
            btm.message_call_for_help(hpf.get_queue_groups_names(queue_keys), online_team))

    if queue_size > 0:
        prev_message = help_queue.map_group_to_message_id.get(list(help_queue.map_group_to_message_id)[-1])
        help_queue.map_group_to_message_id[int(list(help_queue.map_group_to_message_id)[-1])] = help_message.id
        supr = await private_text_channel.fetch_message(prev_message)
        await supr.delete(delay = 0)
    else:
        empty_queue_message = await private_text_channel.send(
                btm.queue_is_empty_message(), delete_after= 10)
        help_queue.empty_queue_message = empty_queue_message.id
        supr1 = await private_text_channel.fetch_message(message_id)
        supr2 = await private_text_channel.fetch_message(help_message.id)
        await supr1.delete(delay = 0)
        await supr2.delete(delay = 0)
        
    return True


async def aux_raise_hand(ctx):
    member = ctx.author
    existing_lab_group = hpf.existing_member_lab_group(member)
    private_text_channel = hpf.get_private_text_channel(ctx.guild)
    if not existing_lab_group:
        await ctx.channel.send(btm.message_member_not_in_group_for_help())
    elif ctx.channel != hpf.existing_member_lab_text_channel(member):
        await ctx.channel.send(btm.error_stay_in_your_seat(ctx.author, existing_lab_group))
    elif private_text_channel:
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
        queue_keys = list(help_queue.map_group_to_message_id.keys())
        queue_keys.append(f"{group_num}")
        if available_team:
            await ctx.channel.send(btm.message_asking_for_help())
            help_message = await private_text_channel.send(
                btm.message_call_for_help(hpf.get_queue_groups_names(queue_keys), available_team))
        elif online_team:
            await ctx.channel.send(btm.message_no_one_available_error())
            help_message = await private_text_channel.send(
                btm.message_call_for_help(hpf.get_queue_groups_names(queue_keys), online_team))
        else:
            await ctx.channel.send(btm.message_no_one_online_error())
        if help_message:
            async with help_queue_lock:
                if queue_size > 0:
                    await ctx.channel.send(btm.info_help_queue_size(queue_size))
                help_queue.add(group=group_num, message_id=help_message.id)
                if queue_size > 0:
                    prev_message = help_queue.map_group_to_message_id.get(list(help_queue.map_group_to_message_id)[-2])
                    supr = await private_text_channel.fetch_message(prev_message)
                    await supr.delete(delay = 0)
                if help_queue.empty_queue_message != 0:
                    supr2 = await private_text_channel.fetch_message(help_queue.empty_queue_message)
                    await supr2.delete(delay = 0)
                    help_queue.empty_queue_message = 0

    else:
        await ctx.channel.send(btm.message_can_not_get_help_error())


async def aux_clear_queue(ctx):
    private_text_channel = hpf.get_private_text_channel(ctx.guild)
    await private_text_channel.send("Queue has been cleaned!")
    help_queue = GUILD_CONFIG.help_queue(ctx.guild)
    prev_message = help_queue.map_group_to_message_id.get(list(help_queue.map_group_to_message_id)[-1])
    supr = await private_text_channel.fetch_message(prev_message)
    await supr.delete(delay = 0)
    GUILD_CONFIG.help_queue(ctx.guild).clear_help_queue()
    return None