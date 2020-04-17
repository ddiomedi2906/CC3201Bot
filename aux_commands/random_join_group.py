import random
from typing import List

import discord

from aux_commands.create_delete_group import aux_create_group
from aux_commands.join_leave_group import get_students_in_group, aux_join_group
from bot import MAX_STUDENTS_PER_GROUP
from utils import bot_messages as btm, helper_functions as hpf

"""
####################################################################
#################### RANDOM JOIN GROUP FUNCTIONS ###################
####################################################################
"""

# TODO: random join
async def aux_random_join(ctx, member: discord.Member, available_existing_groups: List[discord.CategoryChannel]):
    if not member.nick:
        await ctx.send(btm.message_member_need_name_error(member))
        return available_existing_groups
    while len(available_existing_groups) > 0:
        random_lab_group = random.choice(available_existing_groups)
        random_group = hpf.get_lab_group_number(random_lab_group.name)
        if random_group and len(get_students_in_group(ctx, random_group)) < MAX_STUDENTS_PER_GROUP:
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