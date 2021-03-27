#!/usr/bin/env python
# -*- coding: utf-8 -*-
# bot.py
import asyncio
import re
import random
import sys
from asyncio import Lock
from typing import Union, Optional
from datetime import datetime, timedelta

import discord
from discord.ext import commands

# TODO (ddiomedi2906): move all commands imported in aux_commands to LabotaCommands proxy class
from aux_commands import create_delete_group as cdg, join_leave_group as jlg, \
    random_join_group as rjg, raise_hand_for_help as rhh, allow_deny_permissions as adp, list_group as lg
from aux_commands import (
    LabotaCommands,
    # clean_group
    aux_clean_group,
    # misc
    aux_salute,
    aux_broadcast,
    aux_whereis,
    # manage_guild_settings
    aux_init_guild,
    aux_set_guild,
    aux_save_guild,
    # open_close_groups
    aux_open_group,
    aux_close_group,
    is_open_group,
)
from global_variables import *
from utils import bot_messages as btm, helper_functions as hpf
from utils.emoji_utils import same_emoji, get_unicode_from_emoji, get_unicode_emoji_from_alias
from utils.guild_config import GUILD_CONFIG
from utils.my_converters import GuildSettings, LabGroup

# TODO: spanish messages
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
join_make_group_lock = Lock()

"""
####################################################################
############################ EVENTS ################################
####################################################################
"""


@bot.event
async def on_ready():
    # guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
    # guild = discord.utils.get(bot.guilds, id=int(GUILD_ID))
    try:
        print(f'{bot.user} is connected to the following guild:')
        for guild in bot.guilds:
            await aux_init_guild(guild)
        bot.loop.create_task(save_all_task())
        print("Ready to roll!")
    except UnicodeEncodeError as e:
        print(e)
        print("export PYTHONIOENCODING=utf-8")
        sys.exit(2)


@bot.event
async def on_member_join(member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=STUDENT_ROLE_NAME)
    await member.add_roles(role)
    print(f'Role "{role}" assigned to {member}')
    await aux_salute(member, None)
    

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: Union[discord.Member, discord.User]):
    message = reaction.message
    emoji = reaction.emoji
    guild = message.guild
    # bot reacted for marking the message as attended
    if bot.user == user:
        return
    elif message.author == bot.user and re.search(r"calling for help", message.content):
        success = False
        if len(message.reactions) <= 1 and hpf.member_in_teaching_team(user, guild):
            success = await rhh.go_for_help_from_message(user, message, group=hpf.get_lab_group_number(message.content))
        if not success:
            await message.remove_reaction(reaction, user)
    elif message.author == bot.user and len(message.reactions) <= 1:
        if same_emoji(emoji, 'slight_smile'):
            await message.add_reaction(get_unicode_emoji_from_alias('thumbsup'))
            await message.channel.send(emoji)
    else:
        print(emoji, get_unicode_from_emoji(emoji))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MaxConcurrencyReached):
        await ctx.send(f'Only {error.number} concurrent invocations of this command are allowed. Try again in a few seconds.')
    elif isinstance(error, commands.errors.CommandOnCooldown):
        await ctx.send(f'You have to wait {error.retry_after:.3}s before using this command again.')
    elif isinstance(error, commands.errors.CheckFailure):
        await ctx.send(error)
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(error)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(error)
    else:
        await ctx.send(btm.message_default_error())
    print(error)
    # await ctx.send('You do not have the correct role for this command.')

"""
####################################################################
################### CREATE/DELETE GROUP COMMANDS ###################
####################################################################
"""


@bot.command(name='create-group', aliases=["cg", "create"], help='Create a new group.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def create_group(ctx):
    async with ctx.channel.typing():
        await cdg.aux_create_group(ctx)


@bot.command(name='create-many-groups', aliases=["cmg"], help='Create N new groups. (Requires: value for N.)')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def create_many_groups(ctx, num_groups: int):
    async with ctx.channel.typing():
        for _ in range(num_groups):
            await cdg.aux_create_group(ctx)


@bot.command(name='delete-group', aliases=["dg", "delete"], help='Delete a group. (Requires: group number.)')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def delete_group(ctx, group: Union[int, str]):
    async with ctx.channel.typing():
        await cdg.aux_delete_group(ctx, group)


@bot.command(name='delete-all-groups', help='Delete all groups.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def delete_all_groups(ctx):
    async with ctx.channel.typing():
        for group in sorted(hpf.all_existing_lab_groups(ctx.guild), key=lambda c: c.name, reverse=True):
            await cdg.aux_delete_group(ctx, group.name)


@bot.command(name='make-group', aliases=["mkg", "group"], help='Make a group. (Requires: list of members.)')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def make_group_command(ctx, members: commands.Greedy[discord.Member], name_not_valid: Optional[str] = None):
    async with ctx.channel.typing():
        if name_not_valid:
            await ctx.send(btm.message_member_not_exists(name_not_valid))
        else:
            async with join_make_group_lock:
                group = await cdg.aux_make_group(ctx, members)
                if group:
                    await aux_close_group(ctx, group)

"""
####################################################################
##################### JOIN/LEAVE GROUP COMMANDS ####################
####################################################################
"""


@bot.command(name='move', help='Move member to a group. (Requires: member name and group number.)')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def move_to_command(ctx, member_mention: discord.Member, group: Optional[Union[int, str]] = None):
    async with ctx.channel.typing():
        await jlg.aux_move_to(ctx, member_mention, group)


@bot.command(name='join', aliases=["j"], help='Join a group. (Requires: group number.)')
@commands.max_concurrency(number=1)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def join_command(ctx, group: Union[int, str]):
    async with ctx.channel.typing():
        async with join_make_group_lock:
            await jlg.aux_join_group(ctx, ctx.author, group)


@bot.command(name='leave', aliases=["l"], help='Leave your group.')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def leave_command(ctx):
    async with ctx.channel.typing():
        await jlg.aux_leave_group(ctx, ctx.author)


@bot.command(name='invite', aliases=["i"], help='Invite someone to your group. (Requires: member name.)')
@commands.has_any_role(STUDENT_ROLE_NAME)
async def invite_command(ctx, *, member: discord.Member):
    async with ctx.channel.typing():
        await jlg.aux_invite_member(ctx, host_member=ctx.author, invited_member=member)

"""
####################################################################
################## ASSIGNING GROUP COMMANDS ########################
####################################################################
"""


# deprecated
@bot.command(name='random-join', aliases=["rj"], help='Assign a member to a random available group. (Requires: member name.)', hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def random_join_command(ctx, member_mention: discord.Member, *args):
    async with ctx.channel.typing():
        await rjg.aux_random_join(ctx, member_mention, *args)

# deprecated
@bot.command(name='random-join-all', aliases=["rjall"], help='Assign students with no group to a random available group.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def random_join_all_command(ctx, *args):
    async with ctx.channel.typing():
        await rjg.aux_random_join_all(ctx, *args)

@bot.command(name='assign-all', aliases=["assign"], help='Assign online students with no group to an available group.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def assign_all_command(ctx):
    await LabotaCommands.assign_all(ctx)

"""
####################################################################
##################### OPEN/CLOSE GROUPS ############################
####################################################################
"""

@bot.command(name='open', help='Open your group. Anyone can join the group.')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def open_command(ctx, *, group: Optional[LabGroup]):
    async with ctx.channel.typing():
        await aux_open_group(ctx, group)


@bot.command(name='close', help='Close your group. Only invited members can join the group.')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def close_command(ctx, *, group: Optional[LabGroup]):
    async with ctx.channel.typing():
        await aux_close_group(ctx, group)

@bot.command(name='open-group', help='Open a group. (Requires: group number)')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def open_group_command(ctx, *, group: LabGroup):
    async with ctx.channel.typing():
        await aux_open_group(ctx, group)


@bot.command(name='close-group', help='Close a group. (Requires: group number)')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def close_group_command(ctx, *, group: LabGroup):
    async with ctx.channel.typing():
        await aux_close_group(ctx, group)


"""
####################################################################
######################## CLEAN GROUP COMMANDS ######################
####################################################################
"""


@bot.command(name='clean-group', help='Clean group messages and remove members. (Requires: group number.)')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def clean_command(ctx, group: Union[int, str]):
    async with ctx.channel.typing():
        await aux_clean_group(ctx, group)


@bot.command(name='clean-all-groups', help='Clean all group messages and remove their members.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def clean_all_command(ctx, *args):
    async with ctx.channel.typing():
        excluded_groups = hpf.get_excluded_groups(*args)
        groups_to_be_cleaned = [group for group in hpf.all_existing_lab_groups(ctx.guild)
                                if hpf.get_lab_group_number(group.name) not in excluded_groups]
        for group in sorted(groups_to_be_cleaned, key=lambda c: c.name, reverse=False):
            await aux_clean_group(ctx, group.name)

@bot.command(name='clean-open-groups', help='Clean all open group messages and remove their members.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def clean_all_command(ctx, *args):
    async with ctx.channel.typing():
        excluded_groups = hpf.get_excluded_groups(*args)
        groups_to_be_cleaned = [group for group in hpf.all_existing_lab_groups(ctx.guild)
                                if hpf.get_lab_group_number(group.name) not in excluded_groups and is_open_group(ctx.guild, group)]
        for group in sorted(groups_to_be_cleaned, key=lambda c: c.name, reverse=False):
            await aux_clean_group(ctx, group.name)

"""
####################################################################
######################### GROUP LIST ###########################
####################################################################
"""


@bot.command(name='details', help="Show group details.")
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def get_info(ctx, *, group: LabGroup):
    async with ctx.channel.typing():
        await ctx.send(lg.aux_group_details(ctx, group, details=True))


@bot.command(name='list', help='List all groups with their members.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_lab_list(ctx):
    async with ctx.channel.typing():
        await lg.aux_get_list(ctx, message_size=2000)

@bot.command(name='list-online', aliases=["online"], help='List all groups with their currently online members.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_lab_list_online(ctx):
    async with ctx.channel.typing():
        await lg.aux_get_list(ctx, message_size=2000, only_online=True)

@bot.command(name='list-open', aliases=["og","open-groups"], help='List all open groups with their members.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def open_list_command(ctx):
    async with ctx.channel.typing():
        await lg.aux_get_list(ctx, message_size=2000, only_open_groups=True, exclude_empty=False)


"""
####################################################################
################### GROUP PERMISSION EDIT ##########################
####################################################################
"""


@bot.command(name='allow-to', aliases=["at"], help=".", hidden=True)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def allow_to_role(ctx, role_mention: discord.Role, group: int, *args):
    async with ctx.channel.typing():
        await adp.aux_allow_to_role(ctx, role_mention, group, *args)


@bot.command(name='deny-to', aliases=["dt"], help=".", hidden=True)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def deny_to_role(ctx, role_mention: discord.Role, group: int, *args):
    async with ctx.channel.typing():
        await adp.aux_deny_to_role(ctx, role_mention, group, *args)


@bot.command(name='allow-all', aliases=["aall"], help=".", hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def allow_all(ctx, *args):
    async with ctx.channel.typing():
        existing_lab_roles = hpf.all_existing_lab_roles(ctx.guild)
        for existing_lab_role in sorted(existing_lab_roles, key=lambda g: g.name, reverse=True):
            group = hpf.existing_group_number_from_role(existing_lab_role)
            await adp.aux_allow_to_role(ctx, existing_lab_role, group, *args)
        await ctx.send(btm.message_allow_all_success(list(*args), existing_lab_roles))


@bot.command(name='deny-all', aliases=["dall"], help=".", hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def deny_all(ctx, *args):
    async with ctx.channel.typing():
        existing_lab_roles = hpf.all_existing_lab_roles(ctx.guild)
        for existing_lab_role in sorted(existing_lab_roles, key=lambda g: g.name, reverse=True):
            group = hpf.existing_group_number_from_role(existing_lab_role)
            await adp.aux_allow_to_role(ctx, existing_lab_role, group, *args)
        await ctx.send(btm.message_deny_all_success(list(*args), existing_lab_roles))

"""
####################################################################
##################### CALL-FOR-HELP COMMANDS #######################
####################################################################
"""


@bot.command(name='go', aliases=['fly'], help='Go to the next group that has asked for help.')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def go_for_help_command(ctx):
    async with ctx.channel.typing():
        await rhh.aux_go_for_help_from_command(ctx, ctx.author)


@bot.command(name='raise-hand', aliases=[get_unicode_emoji_from_alias('raised_hand'), 'rh'],
             help='Raise your virtual hand asking for any help.')
@commands.cooldown(rate=1, per=2)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def raise_hand(ctx):
    async with ctx.channel.typing():
        await rhh.aux_raise_hand(ctx)


"""
####################################################################
######################### GUILD SETTINGS ###########################
####################################################################
"""


@bot.command(name='init-guild', aliases=["init"], help='Initialize guild settings.', hidden=True)
@commands.cooldown(rate=5, per=1)
@commands.has_guild_permissions(manage_roles=True)
@commands.bot_has_guild_permissions(manage_roles=True)
async def init_guild_command(ctx):
    async with ctx.channel.typing():
        guild = ctx.guild
        if guild not in GUILD_CONFIG:
            await GUILD_CONFIG.init_guild_config(guild)
            await aux_init_guild(guild)
            await ctx.send(btm.success_guild_init(guild))
        else:
            await ctx.send(btm.error_guild_already_init(guild))


@bot.command(name='save-guild', aliases=["save"], help='Save guild settings.', hidden=True)
@commands.cooldown(rate=5, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def save_command(ctx):
    async with ctx.channel.typing():
        await aux_save_guild(ctx)


@bot.command(name='set-guild', aliases=["set"], help='Set guild\'s field.', hidden=True)
@commands.cooldown(rate=5, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def set_guild_command(ctx, *, settings: GuildSettings):
    async with ctx.channel.typing():
        await aux_set_guild(ctx, settings)


"""
####################################################################
############################### MISC ###############################
####################################################################
"""


@bot.command(name='broadcast', help='Broadcast a message to all groups. (Requires: message)')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def broadcast_command(ctx, *, message: str):
    async with ctx.channel.typing():
        await aux_broadcast(ctx, message)


@bot.command(name='whereis', aliases=["w"], help='Find members\' group. (Requires: list of members)')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def where_is_command(ctx, members: commands.Greedy[discord.Member], invalid_name: Optional[str] = None):
    async with ctx.channel.typing():
        await aux_whereis(ctx, members, invalid_name)


@bot.command(name='roll_dice', aliases=["dice"], help='Simulates rolling dice.')
@commands.cooldown(rate=1, per=1)
async def roll(ctx, number_of_sides: int = 6, number_of_dice: int = 1):
    dice = [
        str(random.choice(range(number_of_sides)) + 1)
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(name='salute', help='Say hello to this friendly bot.')
@commands.cooldown(rate=1, per=1)
async def salute(ctx):
    async with ctx.channel.typing():
        await aux_salute(ctx.author, ctx.channel)

"""
####################################################################
###################### PERIODIC EVENTS BOT #########################
####################################################################
"""


async def save_all_task():
    await bot.wait_until_ready()
    guild = bot.get_guild(int(TEST_GUILD_ID))
    general_text_channel = hpf.get_general_text_channel(guild)
    sleep_time = timedelta(hours=12, minutes=0, seconds=0)
    while True:
        await GUILD_CONFIG.save_all()
        now = datetime.now()
        await general_text_channel.send(f"Last config snapshot at {now.strftime('%H:%M:%S %Z on %d %b %Y')}")
        await asyncio.sleep(sleep_time.seconds)

"""
####################################################################
############################ RUN BOT ###############################
####################################################################
"""

def main(argv):
    # print(argv)
    bot.run(TOKEN)


if __name__ == '__main__':
    main(sys.argv[1:])
