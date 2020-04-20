import random
import re
from asyncio import Lock
from typing import Optional, Union, List

import discord
from discord import Role

from aux_commands.open_close_groups import aux_remove_group, open_group
from global_variables import STUDENT_ROLE_NAME
from utils.guild_config import GUILD_CONFIG
from utils.permission_mask import PMask
from aux_commands.join_leave_group import aux_leave_group, aux_join_group
from utils import helper_functions as hpf, bot_messages as btm


"""
####################################################################
############### CREATE/DELETE GROUP AUX FUNCTIONS ##################
####################################################################
"""


async def create_new_role(guild: discord.Guild, role_name: str, **kargs) -> Role:
    existing_role = discord.utils.get(guild.roles, name=role_name)
    if not existing_role:
        new_role = await guild.create_role(name=role_name, **kargs)
        print(f'Creating a new role: {role_name}')
        return new_role
    else:
        await existing_role.edit(**kargs)
        print(f'Role {role_name} already exists!')
        return existing_role


async def update_permission(
        role: discord.Role,
        lab_group: discord.CategoryChannel,
        allow_mask: Optional[int] = None,
        deny_mask: Optional[int] = None
) -> None:
    allow = discord.Permissions(allow_mask) if allow_mask else discord.Permissions()
    denny = discord.Permissions(deny_mask) if deny_mask else discord.Permissions()
    await lab_group.set_permissions(role, overwrite=discord.PermissionOverwrite.from_pair(allow, denny))


async def update_previous_lab_groups_permission(
        role: discord.Role,
        category: discord.CategoryChannel,
        allow_mask: Optional[int] = None,
        deny_mask: Optional[int] = None
) -> None:
    guild = category.guild
    existing_lab_groups = hpf.all_existing_lab_groups(guild)
    for lab_group in existing_lab_groups:
        if lab_group != category:
            await update_permission(role, lab_group, allow_mask, deny_mask)

create_delete_lock = Lock()

async def aux_create_group(ctx) -> Optional[discord.CategoryChannel]:
    async with create_delete_lock:
        # Get existing lab groups
        guild = ctx.guild
        existing_lab_groups = hpf.all_existing_lab_groups(guild)
        # Get new group number (assumes a previous lab group could have been deleted)
        next_num = 1
        for idx, category in enumerate(sorted(existing_lab_groups, key=lambda c: c.name), 2):
            pattern = re.compile(f"Group[\s]+{next_num}")
            if re.search(pattern, category.name) is None:
                break
            next_num = idx
        # Create new names
        new_category_name = hpf.get_lab_group_name(next_num)
        new_role_name = hpf.get_role_name(next_num)
        text_channel_name = hpf.get_text_channel_name(next_num)
        voice_channel_name = hpf.get_voice_channel_name(next_num)
        # Check if category or channels already exist
        existing_category = discord.utils.get(guild.categories, name=new_category_name)
        existing_text_channel = discord.utils.get(guild.channels, name=text_channel_name)
        existing_voice_channel = discord.utils.get(guild.channels, name=voice_channel_name)
        if not (existing_category or existing_text_channel or existing_voice_channel):
            try:
                # Create new role
                new_role = await create_new_role(guild, new_role_name, mentionable=True)
                # Set lab group permissions
                default = discord.Permissions()
                allow_text_voice_stream = discord.Permissions(
                    PMask.VIEW | PMask.PARTIAL_TEXT | PMask.PARTIAL_VOICE | PMask.STREAM)
                can_not_view_channel = discord.Permissions(PMask.VIEW)
                overwrites = {role: discord.PermissionOverwrite.from_pair(default, can_not_view_channel)
                              for role in hpf.all_existing_lab_roles(guild)}
                student_role = discord.utils.get(guild.roles, name=STUDENT_ROLE_NAME)
                if student_role:
                    overwrites[student_role] = discord.PermissionOverwrite.from_pair(default, can_not_view_channel)
                overwrites[new_role] = discord.PermissionOverwrite.from_pair(allow_text_voice_stream, default)
                # Create new lab group
                print(f'Creating a new category: {new_category_name}')
                new_category = await guild.create_category_channel(new_category_name, overwrites=overwrites)
                # Deny access to the lab groups created before
                await update_previous_lab_groups_permission(new_role, new_category, deny_mask=PMask.VIEW)
                # Create new text and voice channels
                print(f'Creating a new channels: ({text_channel_name}) and ({voice_channel_name})')
                text_channel = await new_category.create_text_channel(text_channel_name)
                await new_category.create_voice_channel(voice_channel_name)
                # Success message
                general_channel = discord.utils.get(guild.channels, name=GUILD_CONFIG[guild]["GENERAL_TEXT_CHANNEL_NAME"])
                if general_channel:
                    await general_channel.send(btm.message_group_created(new_category_name, next_num))
                await text_channel.send(btm.message_welcome_group(new_category_name))
                await open_group(guild, new_category)
                return new_category
            except Exception as e:
                print(e)
                await ctx.send(btm.message_unexpected_error("create-group"))
                await aux_delete_group(ctx, next_num, show_bot_message=False)
                raise e


async def aux_delete_group(ctx, group: Union[int, str], show_bot_message: bool = True):
    async with create_delete_lock:
        guild = ctx.guild
        category = hpf.get_lab_group(guild, group)
        role = hpf.get_lab_role(guild, group)
        success = False
        if category:
            channels = category.channels
            for group_member in (role.members if role else []):
                await aux_leave_group(ctx, group_member, show_not_in_group_error=False)
            for channel in channels:
                print(f'Deleting channel: {channel.name}')
                await channel.delete()
            print(f'Deleting category: {category.name}')
            await category.delete()
            await aux_remove_group(guild, category)
            success = True
        elif show_bot_message:
            await ctx.send(btm.message_group_not_exists_error(category.name))
        if role:
            print(f'Deleting role: {role.name}')
            await role.delete()
        if success and show_bot_message:
            general_channel = discord.utils.get(guild.channels, name=GUILD_CONFIG[guild]["GENERAL_TEXT_CHANNEL_NAME"])
            if general_channel:
                await general_channel.send(btm.message_group_deleted(category.name))


async def aux_make_group(ctx, members: List[discord.Member], random_choice: bool = False) -> Optional[discord.CategoryChannel]:
    guild = ctx.guild
    if not hpf.member_in_teaching_team(ctx.author, guild) and ctx.author not in members:
        members.append(ctx.author)
    members = set(members)
    # Check if there are not more members than allowed
    if len(members) > GUILD_CONFIG[guild]["MAX_STUDENTS_PER_GROUP"]:
        await ctx.send(btm.message_too_many_members_error(GUILD_CONFIG[guild]["MAX_STUDENTS_PER_GROUP"]))
        return None
    members_with_groups = False
    # Check if any member is already in any group
    for member in members:
        existing_lab_group = hpf.existing_member_lab_group(member)
        if existing_lab_group:
            members_with_groups = True
            await ctx.send(btm.message_member_already_in_group(hpf.get_nick(member), existing_lab_group.name))
    if members_with_groups:
        return None
    empty_groups = hpf.all_empty_groups(guild)
    if not empty_groups:
        extra_group = await aux_create_group(ctx)
        empty_groups.append(extra_group)
    if random_choice:
        new_group = random.choice(empty_groups)
    else:
        new_group = sorted(empty_groups, key=lambda g: g.name, reverse=False)[0]
    print(f'Moving members {" ".join([hpf.get_nick(m) for m in members])} to {new_group.name}')
    success = True
    for member in members:
        success = success and await aux_join_group(ctx, member, new_group.name)
    if success:
        return new_group
