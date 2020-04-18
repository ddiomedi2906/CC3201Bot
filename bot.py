# bot.py
import re
import random
from typing import Union, List

import discord
from discord.ext import commands

from aux_commands import create_delete_group as cdg, join_leave_group as jlg, \
    random_join_group as rjg, raise_hand_for_help as rhh, allow_deny_permissions as adp, list_group as lg
from aux_commands.clean_group import aux_clean_group
from global_variables import *
from utils import bot_messages as btm, helper_functions as hpf
from utils.emoji_utils import same_emoji, get_unicode_from_emoji, get_unicode_emoji_from_alias
from utils.helper_functions import get_nick
from utils.permission_mask import PMask

# TODO: make-group command
# TODO: set main
# TODO: spanish messages
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
    await cdg.create_new_role(guild, PROFESSOR_ROLE_NAME, permissions=all_allow, colour=discord.Colour.blue(),
                              hoist=True, mentionable=True)
    await cdg.create_new_role(guild, HEAD_TA_ROLE_NAME, permissions=all_allow, colour=discord.Colour.red(),
                              hoist=True, mentionable=True)
    await cdg.create_new_role(guild, TA_ROLE_NAME, permissions=almost_all, colour=discord.Colour.purple(),
                              hoist=True, mentionable=True)
    await cdg.create_new_role(guild, STUDENT_ROLE_NAME, permissions=text_and_voice_allow, colour=discord.Colour.gold(),
                              hoist=True, mentionable=True)
    print("Ready to roll!")


@bot.event
async def on_member_join(member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=STUDENT_ROLE_NAME)
    await member.add_roles(role)
    print(f'Role "{role}" assigned to {member}')
    

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: Union[discord.Member, discord.User]):
    message = reaction.message
    if message.author == bot.user and len(message.reactions) <= 1 and re.search(r"calling for help", message.content):
        if rhh.member_in_teaching_team(user, message.guild) and hpf.existing_member_lab_role(user) is None:
            group = hpf.get_lab_group_number(message.content)
            group_name = hpf.get_lab_group_name(group)
            lab_group = discord.utils.get(user.guild.channels, name=group_name)
            await rhh.go_for_help(user, lab_group, group)
            await reaction.message.channel.send(btm.message_help_on_the_way(user))
        else:
            await message.remove_reaction(reaction, message.author)
    elif message.author == bot.user:
        pass
    else:
        emoji = reaction.emoji
        print(emoji, get_unicode_from_emoji(emoji))
        if same_emoji(emoji, 'slight_smile'):
            await message.add_reaction(get_unicode_emoji_from_alias('thumbsup'))
            await message.channel.send(emoji + emoji + emoji)
            # await message.channel.send(emoji + emoji + emoji)


#@bot.event
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


@bot.command(name='move', help='Move member in a group. Need to provide the group number.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def move_to_command(ctx, member_mention: discord.Member, group: Union[int, str]):
    async with ctx.channel.typing():
        await jlg.aux_move_to(ctx, member_mention, group)


@bot.command(name='join', help='Join to a group. Need to provide the group number.')
@commands.cooldown(rate=1, per=1)
@commands.max_concurrency(number=1)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def join_command(ctx, group: Union[int, str]):
    async with ctx.channel.typing():
        await jlg.aux_join_group(ctx, ctx.author, group)


@bot.command(name='leave', help='Leave a group. Need to provide the group number.')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def leave_command(ctx):
    async with ctx.channel.typing():
        await jlg.aux_leave_group(ctx, ctx.author)

"""
####################################################################
################## RANDOM JOIN GROUP COMMANDS ######################
####################################################################
"""


@bot.command(name='random-join', help='Join to a random available group.')
@commands.cooldown(rate=1, per=1)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def random_join_command(ctx, member_mention: discord.Member, *args):
    async with ctx.channel.typing():
        await rjg.aux_random_join(ctx, member_mention, *args)


@bot.command(name='random-join-all', help='Assign members with no group to a random available group.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def random_join_all_command(ctx, *args):
    async with ctx.channel.typing():
        await rjg.aux_random_join_all(ctx, *args)

"""
####################################################################
######################## CLEAN GROUP COMMANDS ######################
####################################################################
"""


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


@bot.command(name='members', help="List lab group's members.", hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_group_members(ctx, group: int):
    async with ctx.channel.typing():
        message = lg.aux_get_group_members(ctx, group)
        if message:
            await ctx.send(message)


@bot.command(name='lab-list', aliases=["list"], help='List all group with its members.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_lab_list(ctx):
    async with ctx.channel.typing():
        await lg.aux_send_list_by_chunks(ctx)


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


@bot.command(name='raise-hand', aliases=[get_unicode_emoji_from_alias('raised_hand'), 'rh'],
             help='Raise your virtual hand asking for any help.')
@commands.cooldown(rate=1, per=2)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def raise_hand(ctx):
    async with ctx.channel.typing():
        await rhh.aux_raise_hand(ctx)


"""
####################################################################
############################### MISC ###############################
####################################################################
"""


@bot.command(name='whereis', help='Find your group.')
@commands.cooldown(rate=60, per=1)
async def where_is_command(ctx, member: discord.Member):
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
@commands.cooldown(rate=10, per=1)
async def salute(ctx):
    await ctx.send(get_unicode_emoji_from_alias('wave'))
    # await ctx.author.create_dm()
    # await ctx.author.dm_channel.send(f'Hi {ctx.author.name}, welcome to my Discord server!')


"""
####################################################################
############################ RUN BOT ###############################
####################################################################
"""

bot.run(TOKEN)
