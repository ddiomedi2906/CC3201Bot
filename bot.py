# bot.py
import os
import re
import random
from typing import Union, Optional, List
import functools
import operator

import discord
from discord.ext import commands
from dotenv import load_dotenv

from aux_commands import create_delete_group as cdg, join_leave_group as jlg, \
    random_join_group as rjg, raise_hand_for_help as rhh
from utils import bot_messages as btm, helper_functions as hpf
from utils.emoji_utils import same_emoji, get_unicode_from_emoji, get_unicode_emoji_from_alias

# TODO: refactor this file, modularize
# TODO: when leaving a group, move back to general
# TODO: when someome from the teaching team go for help, don't look up mention on message
# TODO: fix list command when messages are too big
# TODO: make-group command
# TODO: set main
# TODO: spanish messages
from utils.helper_functions import get_nick
from utils.permission_mask import PMask

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
# GUILD = os.getenv('DISCORD_GUILD')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')
PROFESSOR_ROLE_NAME = os.getenv('PROFESSOR_ROLE_NAME')
HEAD_TA_ROLE_NAME = os.getenv('AUXILIAR_ROLE_NAME')
TA_ROLE_NAME = os.getenv('ASSISTANT_ROLE_NAME')
STUDENT_ROLE_NAME = os.getenv('STUDENT_ROLE_NAME')
GENERAL_CHANNEL_NAME = os.getenv('GENERAL_CHANNEL_NAME')
MAX_STUDENTS_PER_GROUP = 3
TT_ROLES = [PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME]

bot = commands.Bot(command_prefix='!')

"""
####################################################################
############################ EVENTS ################################
####################################################################
"""


@bot.event
async def on_ready():
    # guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
    guild = discord.utils.get(bot.guilds, id=int(GUILD_ID))
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )
    members = '\n - '.join([get_nick(member) for member in guild.members])
    print(f'Guild Members:\n - {members}')
    all_allow = discord.Permissions.all()
    almost_all = discord.Permissions(PMask.ALL_BUT_ADMIN_AND_GUILD | PMask.STREAM)
    text_and_voice_allow = discord.Permissions(PMask.CHANGE_NICKNAME | PMask.PARTIAL_TEXT | PMask.PARTIAL_VOICE)
    TEST = discord.Permissions(PMask.CHANGE_NICKNAME | PMask.PARTIAL_TEXT | PMask.PARTIAL_VOICE)
    #for permission, value in text_and_voice_allow:
    #    print(f"{value:5}\t{permission}")
    await cdg.create_new_role(guild, PROFESSOR_ROLE_NAME, permissions=all_allow, colour=discord.Colour.blue(), mentionable=True)
    await cdg.create_new_role(guild, HEAD_TA_ROLE_NAME, permissions=all_allow, colour=discord.Colour.red(), hoist=True, mentionable=True)
    await cdg.create_new_role(guild, TA_ROLE_NAME, permissions=almost_all, colour=discord.Colour.purple(), hoist=True, mentionable=True)
    await cdg.create_new_role(guild, STUDENT_ROLE_NAME, permissions=text_and_voice_allow, colour=discord.Colour.gold(), hoist=True, mentionable=True)
    print("Ready to roll!")


@bot.event
async def on_member_join(member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=STUDENT_ROLE_NAME)
    await member.add_roles(role)
    print(f'Role "{role}" assigned to {member}')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if re.search(r"!.+?", message.content):
        await bot.process_commands(message)
    elif message.role_mentions:
        # Check professors
        role_members = discord.utils.get(message.role_mentions, name=PROFESSOR_ROLE_NAME)
        online_member_names = '\n - '.join([get_nick(member) for member in role_members if member.status == discord.Status.online])
        print(f"People available: \n{online_member_names}")
    

@bot.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    if message.author == bot.user and len(message.reactions) <= 1 and re.search(r"calling for help", message.content):
        for member in message.mentions:
            if member == user and hpf.existing_member_lab_role(member) is None:
                group = int(re.match(r"\*\*Group[\s]+(\d+).*", message.content).group(1))
                group_name = hpf.get_lab_group_name(group)
                lab_group = discord.utils.get(user.guild.channels, name=group_name)
                await rhh.go_for_help(member, lab_group, group)
                await reaction.message.channel.send(btm.message_help_on_the_way(member))
                return
        await message.remove_reaction(reaction, message.author)
    if message.author == bot.user:
        return
    emoji = reaction.emoji
    print(emoji, get_unicode_from_emoji(emoji))
    if same_emoji(emoji, 'slight_smile'):
        await message.add_reaction(get_unicode_emoji_from_alias('thumbsup'))
        await message.channel.send(emoji + emoji + emoji)
        # await message.channel.send(emoji + emoji + emoji)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MaxConcurrencyReached):
        print(error)
        await ctx.send(f'Only {error.number} concurred invocations of this command are allowed.')
    elif isinstance(error, commands.errors.CommandOnCooldown):
        print(error)
        await ctx.send(f'You have to wait {error.retry_after:.3}s before using this command again.')
    elif isinstance(error, commands.errors.CheckFailure):
        print(error)
        await ctx.send(error)
    elif isinstance(error, commands.errors.CommandNotFound):
        print(error)
        await ctx.send(error)
    else:
        print(error)
        await ctx.send('You do not have the correct role for this command.')

"""
####################################################################
################### CREATE/DELETE GROUP COMMANDS ###################
####################################################################
"""

@bot.command(name='create-group', help='Create a new lab group.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def create_group(ctx):
    async with ctx.channel.typing():
        await cdg.aux_create_group(ctx)


@bot.command(name='create-many-groups', help='Create N new lab groups.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def create_many_groups(ctx, num_groups: int):
    async with ctx.channel.typing():
        for _ in range(num_groups):
            await cdg.aux_create_group(ctx)


@bot.command(name='delete-group', help='Delete a lab group. Need to provide the group number.', hidden=True)
@commands.cooldown(rate=1, per=5)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def delete_group(ctx, group: Union[int, str]):
    async with ctx.channel.typing():
        await cdg.aux_delete_group(ctx, group)


@bot.command(name='delete-all-groups', help='Delete all lab groups.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def delete_all_groups(ctx):
    async with ctx.channel.typing():
        guild = ctx.guild
        for category in sorted(guild.categories, key=lambda c: c.name, reverse=True):
            if re.search(r"Group[\s]+[0-9]+", category.name):
                await cdg.aux_delete_group(ctx, category.name)

"""
####################################################################
##################### JOIN/LEAVE GROUP COMMANDS ####################
####################################################################
"""

#@bot.command(name='nickname', help='Set your nickname.', hidden=True)
async def nickname_command(ctx, nickname: str):
    await ctx.author.edit(nick=nickname)


@bot.command(name='move', help='Move member in a group. Need to provide the group number.', hidden=True)
@commands.cooldown(rate=1, per=5)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def move_to_command(ctx, member_mention: discord.Member, group: Union[int, str]):
    member = discord.utils.get(ctx.message.mentions, name=member_mention.name)
    if not member:
        await ctx.send(btm.message_member_not_exists(member_mention.nick))
    elif len(jlg.get_students_in_group(ctx, group)) >= MAX_STUDENTS_PER_GROUP:
        await ctx.send(
            btm.message_max_members_in_group_error(hpf.get_lab_group_name(group) if type(group) == int else group,
                                                   MAX_STUDENTS_PER_GROUP))
    else:
        await jlg.aux_leave_group(ctx, member, show_not_in_group_error=False)
        await jlg.aux_join_group(ctx, member, group)


@bot.command(name='join', help='Join to a group. Need to provide the group number.')
@commands.cooldown(rate=1, per=1)
@commands.max_concurrency(number=1)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def join_command(ctx, group: Union[int, str]):
    async with ctx.channel.typing():
        await jlg.aux_join_group(ctx, ctx.author, group)

@bot.command(name='random-join', help='Join to a random available group.')
@commands.cooldown(rate=1, per=1)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def random_join_command(ctx, member_mention: discord.Member, *args):
    async with ctx.channel.typing():
        member = discord.utils.get(ctx.message.mentions, name=member_mention.name)
        if not member:
            await ctx.send(btm.message_member_not_exists(member_mention.nick))
            return
        excluded_groups: List[int] = []
        for arg in args:
            try:
                excluded_groups.append(int(arg))
            except Exception:
                await ctx.send("All extra arguments should be integers!")
                return
        print(excluded_groups)
        available_lab_groups = list(filter(lambda c: re.search(r"Group[\s]+[0-9]+", c.name), ctx.guild.categories))
        await rjg.aux_random_join(ctx, member, [group for group in available_lab_groups if hpf.get_lab_group_number(group.name) and hpf.get_lab_group_number(group.name) not in excluded_groups])

@bot.command(name='random-join-all', help='Assign members with no group to a random available group.', hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def random_join_all_command(ctx, *args):
    async with ctx.channel.typing():
        # Get excluded groups
        excluded_groups: List[int] = []
        for arg in args:
            try:
                excluded_groups.append(int(arg))
            except Exception:
                ctx.send("All extra arguments should be integers!")
                return
        # Get available groups
        available_lab_groups = []
        for group in ctx.guild.categories:
            group_number = hpf.get_lab_group_number(group.name)
            if group_number and group_number not in excluded_groups:
                available_lab_groups.append(group)
        no_group_members = hpf.all_members_with_no_group(ctx.guild)
        # Assign groups
        for member in no_group_members:
            if member != bot.user and member.status == discord.Status.online \
                    and not rhh.member_in_teaching_team(member, ctx.guild, TT_ROLES):
                available_lab_groups = await rjg.aux_random_join(ctx, member, available_lab_groups)


@bot.command(name='leave', help='Leave a group. Need to provide the group number.')
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def leave_command(ctx):
    async with ctx.channel.typing():
        await jlg.aux_leave_group(ctx, ctx.author)

"""
####################################################################
######################## CLEAN GROUP COMMANDS ######################
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
            await jlg.aux_leave_group(ctx, group_member, show_not_in_group_error=False)
        for text_channel in text_channels:
            text_channel_name = text_channel.name
            print(f'Cleaning messages in text channels: ({text_channel_name})')
            await text_channel.purge()
            await text_channel.send(btm.message_welcome_group(category_name))
        await ctx.send(btm.message_group_cleaned(category_name))
    else:
        await ctx.send(btm.message_group_not_exists_error(category_name))

@bot.command(name='clean', help='Clean group messages. Need to provide the group number.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def clean_command(ctx, group: Union[int, str]):
    async with ctx.channel.typing():
        await aux_clean_group(ctx, group)

@bot.command(name='clean-all', help='Clean all groups messages.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def clean_all_command(ctx):
    async with ctx.channel.typing():
        guild = ctx.guild
        for category in sorted(guild.categories, key=lambda c: c.name, reverse=False):
            if re.search(r"Group[\s]+[0-9]+", category.name):
                await aux_clean_group(ctx, category.name)

"""
####################################################################
######################### GROUP LIST ###########################
####################################################################
"""

def aux_get_group_members(ctx, group: Union[int, str], show_empty_error_message: bool = True) -> Optional[str]:
    group = int(re.sub(r"Group[\s]+([0-9]+)", r"\1", group)) if type(group) == str else group
    guild = ctx.guild
    existing_role = hpf.get_lab_role(guild, group)
    if not existing_role:
        return btm.message_group_not_exists_error(group)
    elif not existing_role.members and show_empty_error_message:
        return btm.message_no_members()
    elif existing_role.members:
        return btm.message_list_group_members(group, existing_role.members)
    else:
        return None


@bot.command(name='group-members', help="List lab group's members.", hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_group_members(ctx, group: int):
    async with ctx.channel.typing():
        message = aux_get_group_members(ctx, group)
        if message:
            await ctx.send(message)


@bot.command(name='lab-list', aliases=["list"], help='List all group with its members.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_lab_list(ctx):
    async with ctx.channel.typing():
        guild = ctx.guild
        existing_lab_groups = list(filter(lambda c: re.search(r"Group[\s]+[0-9]+", c.name), guild.categories))
        if not existing_lab_groups:
            await ctx.send(btm.message_no_groups())
            return
        list_string = []
        await ctx.send("Lab list:\n")
        for lab_group in sorted(existing_lab_groups, key=lambda g: g.name):
            message = aux_get_group_members(ctx, lab_group.name, show_empty_error_message=False)
            if message:
                await ctx.send(message)
        #if list_string:
        #    await ctx.send("Lab list:\n" + "\n".join(list_string))

"""
####################################################################
######################### GROUP EDIT ###############################
####################################################################
"""


@bot.group(name='permission', aliases=['p'], invoke_without_command=True, hidden=True)
async def permission_command(ctx):
    await ctx.channel.send("Base `permission` command. \n Subcommands: \n `allow <role> <group> <mask>` \n `deny <role> <group> <mask>` \n `allow-all <mask>` \n `deny-all <mask>`")


@permission_command.command(name='allow-to', aliases=["at"], help=".", hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def allow_to_role(ctx, role_mention: str, group: int, *args):
    async with ctx.channel.typing():
        role = discord.utils.get(ctx.guild.roles, mention=role_mention)
        if role and hpf.get_lab_role(ctx.guild, role.name):
            lab_group = hpf.get_lab_group(ctx.guild, group)
            print(f"Updating allow permissions of {role} on {lab_group}...")
            p_masks = []
            for arg in args:
                if type(arg) == str and PMask.has_key(arg.upper()):
                    p_masks.append(arg.upper())
                else:
                    await ctx.send(btm.message_permission_mask_not_valid(arg))
                    return
            overwrite_mask = functools.reduce(lambda a, b: operator.ior(a, PMask[b]), p_masks, 0)
            await cdg.update_permission(role, lab_group, allow_mask=overwrite_mask)
            await ctx.send(btm.message_allow_to_success(p_masks, role, lab_group))
        elif not role:
            await ctx.send(btm.message_lab_role_not_exists(role_mention))
        else:
            await ctx.send(btm.message_role_permissions_not_modificable_error(role))


@permission_command.command(name='deny-to', aliases=["dt"], help=".", hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def deny_to_role(ctx, role_mention: str, group: int, *args):
    async with ctx.channel.typing():
        role = discord.utils.get(ctx.guild.roles, mention=role_mention)
        if role and hpf.get_lab_role(ctx.guild, role.name):
            lab_group = hpf.get_lab_group(ctx.guild, group)
            print(f"Updating deny permissions of {role} on {lab_group}...")
            p_masks = []
            for arg in args:
                if type(arg) == str and PMask.has_key(arg.upper()):
                    p_masks.append(arg.upper())
                else:
                    await ctx.send(btm.message_permission_mask_not_valid(arg))
                    return
            overwrite_mask = functools.reduce(lambda a, b: operator.ior(a, PMask[b]), p_masks, 0)
            await cdg.update_permission(role, lab_group, deny_mask=overwrite_mask)
            await ctx.send(btm.message_deny_to_success(p_masks, role, lab_group))
        elif not role:
            await ctx.send(btm.message_lab_role_not_exists(role_mention))
        else:
            await ctx.send(btm.message_role_permissions_not_modificable_error(role))


@permission_command.command(name='allow-all', aliases=["aall"], help=".", hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def allow_all(ctx, *args):
    async with ctx.channel.typing():
        existing_lab_roles = hpf.all_existing_lab_roles(ctx.guild)
        p_masks = []
        for arg in args:
            if type(arg) == str and PMask.has_key(arg.upper()):
                p_masks.append(arg.upper())
            else:
                await ctx.send(btm.message_permission_mask_not_valid(arg))
                return
        for existing_lab_role in sorted(existing_lab_roles, key=lambda g: g.name, reverse=True):
            group = hpf.existing_group_number_from_role(existing_lab_role)
            lab_group = hpf.get_lab_group(ctx.guild, group)
            overwrite_mask = functools.reduce(lambda a, b: operator.ior(a, PMask[b]), p_masks, 0)
            print(f"Updating allow permissions on {lab_group}...")
            await cdg.update_previous_lab_groups_permission(existing_lab_role, hpf.get_lab_group(ctx.guild, group), allow_mask=overwrite_mask)
        await ctx.send(btm.message_allow_all_success(p_masks, existing_lab_roles))


@permission_command.command(name='deny-all', aliases=["dall"], help=".", hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def deny_all(ctx, *args):
    async with ctx.channel.typing():
        existing_lab_roles = hpf.all_existing_lab_roles(ctx.guild)
        p_masks = []
        for arg in args:
            if type(arg) == str and PMask.has_key(arg.upper()):
                p_masks.append(arg.upper())
            else:
                await ctx.send(f"{arg} is not a valid permission mask!")
                return
        for existing_lab_role in sorted(existing_lab_roles, key=lambda g: g.name, reverse=True):
            group = hpf.existing_group_number_from_role(existing_lab_role)
            lab_group = hpf.get_lab_group(ctx.guild, group)
            overwrite_mask = functools.reduce(lambda a, b: operator.ior(a, PMask[b]), p_masks, 0)
            print(f"Updating deny permissions on {lab_group}...")
            await cdg.update_previous_lab_groups_permission(existing_lab_role, hpf.get_lab_group(ctx.guild, group), deny_mask=overwrite_mask)
        await ctx.send(btm.message_deny_all_success(p_masks, existing_lab_roles))

"""
####################################################################
##################### CALL-FOR-HELP COMMANDS #######################
####################################################################
"""


@bot.command(name='raise-hand', aliases=[get_unicode_emoji_from_alias('raised_hand'), 'rh'], help='Raise your virtual hand asking for any help.')
@commands.cooldown(rate=1, per=2)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def raise_hand(ctx):
    async with ctx.channel.typing():
        await rhh.aux_raise_hand(ctx, GENERAL_CHANNEL_NAME, TT_ROLES)


"""
####################################################################
############################### MISC ###############################
####################################################################
"""

@bot.command(name='whereis', help='Find your group.')
@commands.cooldown(rate=60, per=1)
async def whereis_command(ctx, member: discord.Member):
    lab_group = hpf.existing_member_lab_group(member)
    if lab_group:
        await ctx.send(btm.message_where_is_member(member, lab_group))
    else:
        await ctx.send(btm.message_member_not_in_group(get_nick(member)))


@bot.command(name='roll_dice', help='Simulates rolling dice.')
@commands.cooldown(rate=1, per=1)
async def roll(ctx, number_of_dice: int=1, number_of_sides: int=6):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(name='salute', help='Say hello to this friendly bot.')
@commands.cooldown(rate=60, per=1)
async def salute(ctx):
    await ctx.send(get_unicode_emoji_from_alias('wave'))
    # await ctx.author.create_dm()
    #await ctx.author.dm_channel.send(f'Hi {ctx.author.name}, welcome to my Discord server!')


"""
####################################################################
############################ RUN BOT ###############################
####################################################################
"""

bot.run(TOKEN)