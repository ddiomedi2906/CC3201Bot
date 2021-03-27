import random
from typing import List

import discord

from aux_commands.create_delete_group import aux_create_group
from aux_commands.join_leave_group import aux_join_group
from aux_commands.open_close_groups import is_open_group
from utils import bot_messages as btm, helper_functions as hpf
from utils.guild_config import GUILD_CONFIG

"""
####################################################################
#################### RANDOM JOIN GROUP FUNCTIONS ###################
####################################################################
"""

# TODO: random join
async def random_assignment(ctx, member: discord.Member, available_existing_groups: List[discord.CategoryChannel]):
    if not member.nick:
        await ctx.send(btm.message_member_need_name_error(member))
        return available_existing_groups
    max_group_size = GUILD_CONFIG.max_students_per_group(ctx.guild)
    while len(available_existing_groups) > 0:
        random_lab_group = random.choice(available_existing_groups)
        random_group = hpf.get_lab_group_number(random_lab_group.name)
        if random_group and len(hpf.all_students_in_group(ctx.guild, random_group)) < max_group_size:
            success = await aux_join_group(ctx, member, random_group)
            if success:
                return available_existing_groups
        available_existing_groups.remove(random_lab_group)
    new_group = await aux_create_group(ctx)
    new_group_number = hpf.get_lab_group_number(new_group.name)
    if await aux_join_group(ctx, member, new_group_number):
        ctx.send(btm.message_default_error())
    available_existing_groups.append(new_group)
    return available_existing_groups


async def aux_random_join(ctx, member_mention: discord.Member, *args):
    member = discord.utils.get(ctx.message.mentions, name=member_mention.name)
    excluded_groups = hpf.get_excluded_groups(*args)
    if not member:
        await ctx.send(btm.message_member_not_exists(member_mention.nick))
    elif not excluded_groups:
        await ctx.send("All extra arguments should be integers for excluded groups.")
    else:
        available_lab_groups = []
        for group in hpf.all_existing_lab_groups(ctx.guild):
            group_number = hpf.get_lab_group_number(group.name)
            if group_number and group not in excluded_groups and is_open_group(ctx.guild, group):
                available_lab_groups.append(group)
        await random_assignment(ctx, member, available_lab_groups)


async def aux_random_join_all(ctx, *args):
    # Get excluded groups
    excluded_groups = hpf.get_excluded_groups(*args)
    #if not excluded_groups:
    #    await ctx.send("All extra arguments should be integers for excluded groups.")
    #    return
    # Get available groups
    available_lab_groups = []
    for group in hpf.all_existing_lab_groups(ctx.guild):
        group_number = hpf.get_lab_group_number(group.name)
        if group_number and group not in excluded_groups and is_open_group(ctx.guild, group):
            available_lab_groups.append(group)
    no_group_members = hpf.all_students_with_no_group(ctx.guild)
    # Assign groups
    for member in no_group_members:
        # if member.status == discord.Status.online:
        available_lab_groups = await random_assignment(ctx, member, available_lab_groups)
