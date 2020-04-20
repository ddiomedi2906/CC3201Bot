# bot.py
import re
import random
import sys
from asyncio import Lock
from typing import Union, Optional

import discord
from discord.ext import commands

from aux_commands import create_delete_group as cdg, join_leave_group as jlg, \
    random_join_group as rjg, raise_hand_for_help as rhh, allow_deny_permissions as adp, list_group as lg
from aux_commands.clean_group import aux_clean_group
from aux_commands.init_functions import init_guild
from aux_commands.open_close_groups import aux_open_group, aux_close_group
from global_variables import *
from utils import bot_messages as btm, helper_functions as hpf
from utils.emoji_utils import same_emoji, get_unicode_from_emoji, get_unicode_emoji_from_alias
from utils.guild_config import GUILD_CONFIG
from utils.helper_functions import get_nick
from utils.my_converters import GuildSettings, LabGroup

# TODO: opened and closed groups
# TODO: queue message
# TODO: set main
# TODO: spanish messages
bot = commands.Bot(command_prefix='!')
join_make_group_lock = Lock()
open_close_lock = Lock()

"""
####################################################################
############################ EVENTS ################################
####################################################################
"""


@bot.event
async def on_ready():
    # guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
    # guild = discord.utils.get(bot.guilds, id=int(GUILD_ID))
    print(f'{bot.user} is connected to the following guild:\n')
    for guild in bot.guilds:
        await init_guild(guild)
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
        if hpf.member_in_teaching_team(user, message.guild) and hpf.existing_member_lab_role(user) is None:
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


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MaxConcurrencyReached):
        await ctx.send(f'Only {error.number} concurred invocations of this command are allowed.')
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
    print(error)
    # await ctx.send('You do not have the correct role for this command.')

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
        for group in sorted(hpf.all_existing_lab_groups(ctx.guild), key=lambda c: c.name, reverse=True):
            await cdg.aux_delete_group(ctx, group.name)


@bot.command(name='group', aliases=["make-group"], help='Make a group with the given members.', hidden=True)
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
        async with join_make_group_lock:
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
##################### OPEN/CLOSE GROUPS ############################
####################################################################
"""


@bot.command(name='open', help='Open group. Anyone can join the group.', hidden=True)
async def open_command(ctx, *, group: LabGroup):
    async with ctx.channel.typing():
        async with open_close_lock:
            await aux_open_group(ctx, group)


@bot.command(name='close', help='Close group. No one can join the group.', hidden=True)
async def close_command(ctx, *, group: LabGroup):
    async with ctx.channel.typing():
        async with open_close_lock:
            await aux_close_group(ctx, group)


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
        for group in sorted(hpf.all_existing_lab_groups(ctx.guild), key=lambda c: c.name, reverse=False):
            await aux_clean_group(ctx, group.name)

"""
####################################################################
######################### GROUP LIST ###########################
####################################################################
"""


@bot.command(name='info', help="Show group details.")
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def get_info(ctx, *, group: LabGroup):
    async with ctx.channel.typing():
        await ctx.send(lg.aux_group_details(ctx, group, details=True))


@bot.command(name='lab-list', aliases=["list"], help='List all group with its members.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_lab_list(ctx):
    async with ctx.channel.typing():
        await lg.aux_get_list(ctx, message_size=2000)


@bot.command(name='isopen', help='List all open group with its members.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_lab_list(ctx):
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


@bot.command(name='save', help='Save guild settings.', hidden=True)
@commands.cooldown(rate=5, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def save_command(ctx):
    async with ctx.channel.typing():
        if await GUILD_CONFIG.save(ctx.guild):
            await ctx.send(btm.success_guild_settings_saved(ctx.guild))
        else:
            await btm.message_unexpected_error("save")


@bot.command(name='set', help='Set guild\'s field.', hidden=True)
@commands.cooldown(rate=5, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def set_command(ctx, *, settings: GuildSettings):
    async with ctx.channel.typing():
        guild = ctx.guild
        has_values = False
        if guild not in GUILD_CONFIG:
            await ctx.send(btm.message_default_error())
            print(f"Guild {guild.name} is not included on config.json!")
            return
        print(f"Setting values on guild {guild.name}...")
        for key, value in settings.items:
            if value is not None:
                has_values = True
                GUILD_CONFIG[guild][key] = value
                print(f"{key}: {value}")
        if has_values:
            await ctx.send(btm.success_guild_settings_changed(guild))


"""
####################################################################
############################### MISC ###############################
####################################################################
"""


@bot.command(name='broadcast', help='Broadcast a message on all groups.', hidden=True)
@commands.cooldown(rate=60, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def broadcast_command(ctx, *, message: str):
    async with ctx.channel.typing():
        guild = ctx.guild
        general_text_channel = discord.utils.get(guild.text_channels,
                                                 name=GUILD_CONFIG[guild]["GENERAL_TEXT_CHANNEL_NAME"])
        existing_lab_groups = hpf.all_existing_lab_groups(guild)
        await general_text_channel.send(btm.broadcast_message_from(ctx.author, message))
        for group in existing_lab_groups:
            text_channel = hpf.get_lab_text_channel(guild, group.name)
            await text_channel.send(btm.broadcast_message_from(ctx.author, message))


@bot.command(name='whereis', help='Find your group.')
@commands.cooldown(rate=60, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def where_is_command(ctx, members: commands.Greedy[discord.Member], name_not_valid: Optional[str] = None):
    async with ctx.channel.typing():
        if name_not_valid:
            await ctx.send(btm.message_member_not_exists(name_not_valid))
        for member in members:
            lab_group = hpf.existing_member_lab_group(member)
            if lab_group:
                await ctx.send(btm.message_where_is_member(member, lab_group))
            else:
                await ctx.send(btm.message_member_not_in_any_group(get_nick(member)))


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

def main(argv):
    """
    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["envpath=", "lang="])
    except getopt.GetoptError:
        print('test.py -i <inputfile> -o <outputfile>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('test.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    """
    bot.run(TOKEN)

if __name__ == '__main__':
    main(sys.argv[1:])