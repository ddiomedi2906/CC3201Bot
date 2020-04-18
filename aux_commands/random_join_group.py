import random
from typing import List, Optional

import discord

from aux_commands.create_delete_group import aux_create_group
from aux_commands.join_leave_group import get_students_in_group, aux_join_group
from aux_commands.raise_hand_for_help import member_in_teaching_team
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
    MAX_GROUP_SIZE = GUILD_CONFIG[ctx.guild]["MAX_STUDENTS_PER_GROUP"]
    while len(available_existing_groups) > 0:
        random_lab_group = random.choice(available_existing_groups)
        random_group = hpf.get_lab_group_number(random_lab_group.name)
        if random_group and len(get_students_in_group(ctx, random_group)) < MAX_GROUP_SIZE:
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


def get_excluded_groups(*args) -> Optional[List[int]]:
    excluded_groups: List[int] = []
    for arg in args:
        try:
            excluded_groups.append(int(arg))
        except ValueError:
            return None
    return excluded_groups


async def aux_random_join(ctx, member_mention: discord.Member, *args):
    member = discord.utils.get(ctx.message.mentions, name=member_mention.name)
    excluded_groups = get_excluded_groups(*args)
    if not member:
        await ctx.send(btm.message_member_not_exists(member_mention.nick))
    elif not excluded_groups:
        await ctx.send("All extra arguments should be integers!")
    else:
        available_lab_groups = []
        for group in hpf.all_existing_lab_groups(ctx.guild):
            group_number = hpf.get_lab_group_number(group.name)
            if group_number and group not in excluded_groups:
                available_lab_groups.append(group)
        await random_assignment(ctx, member, available_lab_groups)


async def aux_random_join_all(ctx, *args):
    # Get excluded groups
    excluded_groups = get_excluded_groups(*args)
    if not excluded_groups:
        await ctx.send("All extra arguments should be integers!")
        return
    # Get available groups
    available_lab_groups = []
    for group in hpf.all_existing_lab_groups(ctx.guild):
        group_number = hpf.get_lab_group_number(group.name)
        if group_number and group not in excluded_groups:
            available_lab_groups.append(group)
    no_group_members = hpf.all_members_with_no_group(ctx.guild)
    # Assign groups
    for member in no_group_members:
        if not member.bot and member.status == discord.Status.online \
                and not member_in_teaching_team(member, ctx.guild):
            available_lab_groups = await random_assignment(ctx, member, available_lab_groups)
