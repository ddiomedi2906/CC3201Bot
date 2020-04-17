import functools
import operator
from typing import Optional

import discord

from utils import bot_messages as btm, helper_functions as hpf
from utils.permission_mask import PMask

from aux_commands import create_delete_group as cdg

def get_permission_mask(*args) -> Optional[int]:
    p_masks = []
    for arg in args:
        if type(arg) == str and PMask.has_key(arg.upper()):
            p_masks.append(arg.upper())
        else:
            return
    return functools.reduce(lambda a, b: operator.ior(a, PMask[b]), p_masks, 0)


async def aux_allow_to_role(ctx, role_mention: discord.Role, group: int, *args):
    role = discord.utils.get(ctx.guild.roles, mention=role_mention.name)
    if role and hpf.get_lab_role(ctx.guild, role.name):
        lab_group = hpf.get_lab_group(ctx.guild, group)
        print(f"Updating allow permissions of {role} on {lab_group}...")
        overwrite_mask = get_permission_mask(*args)
        if not overwrite_mask:
            await ctx.send(btm.message_permission_mask_not_valid("|".join(*args)))
        else:
            await cdg.update_permission(role, lab_group, allow_mask=overwrite_mask)
            await ctx.send(btm.message_allow_to_success(list(*args), role, lab_group))
    elif not role:
        await ctx.send(btm.message_lab_role_not_exists(role_mention.name))
    else:
        await ctx.send(btm.message_role_permissions_not_modificable_error(role))


async def aux_deny_to_role(ctx, role_mention: discord.Role, group: int, *args):
    role = discord.utils.get(ctx.guild.roles, mention=role_mention.name)
    if role and hpf.get_lab_role(ctx.guild, role.name):
        lab_group = hpf.get_lab_group(ctx.guild, group)
        print(f"Updating deny permissions of {role} on {lab_group}...")
        overwrite_mask = get_permission_mask(*args)
        if not overwrite_mask:
            await ctx.send(btm.message_permission_mask_not_valid("|".join(*args)))
        else:
            await cdg.update_permission(role, lab_group, deny_mask=overwrite_mask)
            await ctx.send(btm.message_deny_to_success(list(*args), role, lab_group))
    elif not role:
        await ctx.send(btm.message_lab_role_not_exists(role_mention.name))
    else:
        await ctx.send(btm.message_role_permissions_not_modificable_error(role))