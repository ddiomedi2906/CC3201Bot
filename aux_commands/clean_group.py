from typing import Union

import discord

from aux_commands import join_leave_group as jlg
from utils import helper_functions as hpf, bot_messages as btm

"""
####################################################################
################### CLEAN GROUP HELPER FUNCTIONS ###################
####################################################################
"""

async def aux_clean_group(ctx, group: Union[int, str]):
    guild = ctx.guild
    category_name = hpf.get_lab_group_name(group) if type(group) == int else group
    role_name = f"member-{category_name.lower()}"
    category = discord.utils.get(guild.categories, name=category_name)
    existing_role = discord.utils.get(guild.roles, name=role_name)
    if category and existing_role:
        text_channels = category.text_channels
        for group_member in (existing_role.members if existing_role else []):
            await jlg.aux_leave_group(ctx, group_member, show_open_message=False)
        for text_channel in text_channels:
            text_channel_name = text_channel.name
            print(f'Cleaning messages in text channels: ({text_channel_name})')
            await text_channel.purge()
            await text_channel.send(btm.message_welcome_group(category_name))
        await ctx.send(btm.message_group_cleaned(category_name))
    else:
        await ctx.send(btm.message_group_not_exists_error(category_name))