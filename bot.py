# bot.py
import os
import random
import re
from enum import IntFlag
from typing import Union, Optional, List

import discord
from discord import Role
from discord.ext import commands
from dotenv import load_dotenv

from utils import bot_messages as btm
from utils import helper_functions as hpf
from utils.emoji_utils import same_emoji, get_unicode_from_emoji, get_unicode_emoji_from_alias

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

bot = commands.Bot(command_prefix='!')

class PMask(IntFlag):
    STREAM = 512
    VIEW = 1024
    CHANGE_NICKNAME = 67108864
    PARTIAL_TEXT = 129088
    PARTIAL_VOICE = 49283072
    ALL_BUT_ADMIN_AND_GUILD = 1341652291


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
    members = '\n - '.join([member.name for member in guild.members])
    print(f'Guild Members:\n - {members}')
    all_allow = discord.Permissions.all()
    almost_all = discord.Permissions(PMask.ALL_BUT_ADMIN_AND_GUILD | PMask.STREAM)
    text_and_voice_allow = discord.Permissions(PMask.PARTIAL_TEXT | PMask.PARTIAL_VOICE)
    TEST = discord.Permissions(PMask.CHANGE_NICKNAME | PMask.PARTIAL_TEXT | PMask.PARTIAL_VOICE)
    for permission, value in TEST:
        print(f"{value:5}\t{permission}")
    await create_new_role(guild, PROFESSOR_ROLE_NAME, permissions=all_allow, colour=discord.Colour.blue(), mentionable=True)
    await create_new_role(guild, HEAD_TA_ROLE_NAME, permissions=all_allow, colour=discord.Colour.red(), hoist=True, mentionable=True)
    await create_new_role(guild, TA_ROLE_NAME, permissions=almost_all, colour=discord.Colour.purple(), hoist=True, mentionable=True)
    await create_new_role(guild, STUDENT_ROLE_NAME, permissions=text_and_voice_allow, colour=discord.Colour.gold(), hoist=True, mentionable=True)
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
    if message.role_mentions:
        available_people = []
        # Check professors
        professor_mention = discord.utils.get(message.role_mentions, name=PROFESSOR_ROLE_NAME)
        available_people.extend(get_available_members_from_role(professor_mention))
        # Check Head TAs
        auxiliar_mention = discord.utils.get(message.role_mentions, name=HEAD_TA_ROLE_NAME)
        available_people.extend(get_available_members_from_role(auxiliar_mention))
        # Check TAs
        assistant_mention = discord.utils.get(message.role_mentions, name=TA_ROLE_NAME)
        available_people.extend(get_available_members_from_role(assistant_mention))
        print(f"People available: {' - '.join([member.name for member in available_people])}")
    if re.search(r"!.+?", message.content):
        await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    if message.author == bot.user and re.search(r"calling for help", message.content):
        for member in message.mentions:
            if member == user and hpf.existing_member_lab_role(member) is None:
                group = int(re.match(r"\*\*Group[\s]+(\d+).*", message.content).group(1))
                group_name = hpf.get_lab_group_name(group)
                lab_group = discord.utils.get(user.guild.channels, name=group_name)
                await go_for_help(member, lab_group, group)
                await reaction.message.channel.send(btm.message_help_on_the_way(member))
                return
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
    existing_lab_groups = list(filter(lambda c: re.search(r"Group[\s]+[0-9]+", c.name) and c != category, guild.categories))
    for lab_group in existing_lab_groups:
        await update_permission(role, lab_group, allow_mask, deny_mask)


async def aux_create_group(ctx):
    # Get existing lab groups
    guild = ctx.guild
    existing_lab_groups = list(filter(lambda c: re.search(r"Group[\s]+[0-9]+", c.name), guild.categories))
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
            allow_text_voice_stream = discord.Permissions(PMask.VIEW | PMask.PARTIAL_TEXT | PMask.PARTIAL_VOICE | PMask.STREAM)
            can_not_view_channel = discord.Permissions(PMask.VIEW)
            overwrites = {role: discord.PermissionOverwrite.from_pair(default, can_not_view_channel)
                          for role in hpf.all_existing_lab_roles(guild)}
            student_role = discord.utils.get(guild.roles, name=STUDENT_ROLE_NAME)
            if student_role:
                overwrites[student_role] = discord.PermissionOverwrite.from_pair(default, can_not_view_channel)
            overwrites[new_role] = discord.PermissionOverwrite.from_pair(allow_text_voice_stream, default)
            # Create new lab group
            print(f'Creating a new category: {new_category_name}')
            new_category = await guild.create_category_channel(new_category_name , overwrites=overwrites)
            # Deny access to the lab groups created before
            await update_previous_lab_groups_permission(new_role, new_category, deny_mask=PMask.VIEW)
            # Create new text and voice channels
            print(f'Creating a new channels: ({text_channel_name}) and ({voice_channel_name})')
            await guild.create_text_channel(text_channel_name, category=new_category)
            await guild.create_voice_channel(voice_channel_name, category=new_category)
            # Success message
            general_channel = discord.utils.get(guild.channels, name=GENERAL_CHANNEL_NAME)
            if general_channel:
                await general_channel.send(btm.message_group_created(new_category_name, next_num))
        except Exception as e:
            print(e)
            await ctx.send(btm.message_unexpected_error("create-group"))
            await aux_delete_group(ctx, next_num, show_bot_message=False)
            raise e


async def aux_delete_group(ctx, group: Union[int, str], show_bot_message: bool = True):
    guild = ctx.guild
    category_name = hpf.get_lab_group_name(group) if type(group) == int else group
    role_name = f"member-{category_name.lower()}"
    category = discord.utils.get(guild.categories, name=category_name)
    role = discord.utils.get(guild.roles, name=role_name)
    success = False
    if category:
        channels = category.channels
        for group_member in (role.members if role else []):
            await leave_group(ctx, group_member, show_not_in_group_error=False)
        for channel in channels:
            print(f'Deleting channel: {channel.name}')
            await channel.delete()
        print(f'Deleting category: {category.name}')
        await category.delete()
        success = True
    elif show_bot_message:
        await ctx.send(btm.message_group_not_exists_error(category_name))
    if role:
        print(f'Deleting role: {role.name}')
        await role.delete()
    if success and show_bot_message:
        general_channel = discord.utils.get(guild.channels, name=GENERAL_CHANNEL_NAME)
        if general_channel:
            await general_channel.send(btm.message_group_deleted(category_name))

"""
####################################################################
################### CREATE/DELETE GROUP COMMANDS ###################
####################################################################
"""


@bot.command(name='create-group', help='Create a new lab group.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def create_group(ctx):
    await aux_create_group(ctx)


@bot.command(name='create-many-groups', help='Create N new lab groups.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def create_many_groups(ctx, num_groups: int):
    for _ in range(num_groups):
        await aux_create_group(ctx)


@bot.command(name='delete-group', help='Delete a lab group. Need to provide the group number.', hidden=True)
@commands.cooldown(rate=1, per=5)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def delete_group(ctx, group: Union[int, str]):
    await aux_delete_group(ctx, group)


@bot.command(name='delete-all-groups', help='Delete all lab groups.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def delete_all_groups(ctx):
    guild = ctx.guild
    for category in sorted(guild.categories, key=lambda c: c.name, reverse=True):
        if re.search(r"Group[\s]+[0-9]+", category.name):
            await aux_delete_group(ctx, category.name)

"""
####################################################################
##################### JOIN/LEAVE GROUP FUNCTIONS ###################
####################################################################
"""

def get_students_in_group(ctx, group: Union[int, str]) -> List[discord.Member]:
    guild = ctx.guild
    existing_role = discord.utils.get(guild.roles, name=hpf.get_role_name(group) if type(group) == int else group)
    student_role = discord.utils.get(guild.roles, name=STUDENT_ROLE_NAME)
    if not existing_role:
        return []
    return [member for member in guild.members if existing_role in member.roles and student_role in member.roles]


async def join_group(ctx, member: discord.Member, group: Union[int, str]):
    guild = ctx.guild
    new_role = discord.utils.get(guild.roles, name=hpf.get_role_name(group) if type(group) == int else group)
    new_lab_group_name = hpf.get_lab_group_name(group) if type(group) == int else group
    existing_lab_group = hpf.existing_member_lab_role(member)
    if existing_lab_group:
        await ctx.send(btm.message_member_already_in_group(member.name, existing_lab_group.name))
    elif not new_role:
        await ctx.send(btm.message_lab_group_not_exists(new_lab_group_name))
    elif len(get_students_in_group(ctx, group)) >= MAX_STUDENTS_PER_GROUP:
        await ctx.send(btm.message_max_members_in_group_error(new_lab_group_name, MAX_STUDENTS_PER_GROUP))
    else:
        await member.add_roles(new_role)
        print(f'Role "{new_role}" assigned to {member}')
        # Move to voice channel if connected
        voice_channel = discord.utils.get(guild.channels,
                                          name=hpf.get_voice_channel_name(group) if type(group) == int else group)
        if voice_channel and member.voice and member.voice.channel:
            await member.move_to(voice_channel)
        # Message to group text channel
        text_channel = discord.utils.get(guild.channels,
                                         name=hpf.get_text_channel_name(group) if type(group) == int else group)
        if text_channel:
            await text_channel.send(btm.message_mention_member_when_join_group(member, new_lab_group_name))
        # Message to general channel
        general_channel = discord.utils.get(guild.channels, name=GENERAL_CHANNEL_NAME)
        if general_channel:
            await general_channel.send(btm.message_member_joined_group(member.name, new_lab_group_name))



async def leave_group(ctx, member: discord.Member, show_not_in_group_error: bool = True):
    guild = ctx.guild
    existing_lab_role = hpf.existing_member_lab_role(member)
    if existing_lab_role:
        await member.remove_roles(existing_lab_role)
        print(f'Role "{existing_lab_role}" removed to {member}')
        # Disconnect from the group voice channel if connected to it
        voice_channel = hpf.existing_member_lab_voice_channel(member)
        if voice_channel and member.voice and member.voice.channel == voice_channel:
            await member.move_to(None)
        # Message to group text channel
        text_channel = hpf.existing_member_lab_text_channel(member)
        if text_channel:
            await text_channel.send(btm.message_member_left_group(member.name, existing_lab_role.name))
        # Message to general channel
        general_channel = discord.utils.get(guild.channels, name=GENERAL_CHANNEL_NAME)
        if general_channel:
            await general_channel.send(btm.message_member_left_group(member.name, existing_lab_role.name))
    elif show_not_in_group_error:
        await ctx.send(btm.message_member_not_in_group(member.name))

"""
####################################################################
##################### JOIN/LEAVE GROUP COMMANDS ####################
####################################################################
"""

@bot.group(name='group', invoke_without_command=True)
async def labgroup_command(ctx):
    await ctx.channel.send("Base `labgroup` command. Subcommands: `join <num>` - `leave <num>`")

@labgroup_command.command(name='move', help='Move member in a group. Need to provide the group number.', hidden=True)
@commands.cooldown(rate=1, per=5)
@commands.max_concurrency(number=1)
@commands.has_any_role(HEAD_TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def group_move_to_subcommand(ctx, member_name: str, group: Union[int, str]):
    guild = ctx.guild
    member = discord.utils.get(guild.members, name=member_name)
    if not member:
        await ctx.send(btm.message_member_not_exists(member_name))
    elif len(get_students_in_group(ctx, group)) >= MAX_STUDENTS_PER_GROUP:
        await ctx.send(
            btm.message_max_members_in_group_error(hpf.get_lab_group_name(group) if type(group) == int else group,
                                                   MAX_STUDENTS_PER_GROUP))
    else:
        await leave_group(ctx, member, show_not_in_group_error=False)
        await join_group(ctx, member, group)


@labgroup_command.command(name='join', help='Join to a group. Need to provide the group number.')
@commands.cooldown(rate=1, per=1)
@commands.max_concurrency(number=1)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def group_join_subcommand(ctx, group: Union[int, str]):
    await join_group(ctx, ctx.author, group)



@labgroup_command.command(name='leave', help='Leave a group. Need to provide the group number.')
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def group_leave_subcommand(ctx, group: Union[int, str], member_name: Optional[str] = None):
    await leave_group(ctx, ctx.author)

"""
####################################################################
######################### GROUP LIST ###########################
####################################################################
"""

def aux_get_group_members(ctx, group: Union[int, str], show_empty_error_message: bool = True) -> Optional[str]:
    group = int(re.sub(r"Group[\s]+([0-9]+)", r"\1", group)) if type(group) == str else group
    guild = ctx.guild
    role_name = hpf.get_role_name(group)
    existing_role = discord.utils.get(guild.roles, name=role_name)
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
    message = aux_get_group_members(ctx, group)
    if message:
        await ctx.send(message)


@bot.command(name='lab-list', help='List all group with its members.', hidden=True)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_lab_list(ctx):
    guild = ctx.guild
    existing_lab_groups = list(filter(lambda c: re.search(r"Group[\s]+[0-9]+", c.name), guild.categories))
    if not existing_lab_groups:
        await ctx.send(btm.message_no_groups())
        return
    list_string = []
    for lab_group in sorted(existing_lab_groups, key=lambda g: g.name):
        message = aux_get_group_members(ctx, lab_group.name, show_empty_error_message=False)
        if message:
            list_string.append(message)
    if list_string:
        await ctx.send("Lab list:\n" + "\n".join(list_string))

"""
####################################################################
######################### GROUP EDIT ###############################
####################################################################
"""

@bot.group(name='permission', aliases=['p'], invoke_without_command=True)
async def permission_command(ctx):
    await ctx.channel.send("Base `permission` command. \n Subcommands: `allow <group> <mask>` \n `deny <group> <mask>` \n `allow-all <mask>` \n `deny-all <mask>`")

@permission_command.command(name='show', help=".", hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def show_permissions(ctx, group: int):
    existing_lab_group = hpf.get_lab_group(ctx.guild, group)
    if existing_lab_group:
        lab_group_overwrites = existing_lab_group.overwrites
        existing_lab_role = hpf.get_lab_role(ctx.guild, group)
        if existing_lab_role and existing_lab_role in lab_group_overwrites:
            for permission, value in lab_group_overwrites[existing_lab_role]:
                print(permission, value, sep='\t')
        else:
            print(f"Role {existing_lab_role} does not have overwrites in {existing_lab_group}")
    else:
        print(f"Group {group} does not exists!")

@permission_command.command(name='deny-all', help=".", hidden=True)
@commands.cooldown(rate=1, per=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def deny_all(ctx, mask: int):
    existing_lab_roles = hpf.all_existing_lab_roles(ctx.guild)
    print(ctx.guild.name)
    for existing_lab_role in sorted(existing_lab_roles, key=lambda g: g.name, reverse=True):
        group = hpf.existing_group_number_from_role(existing_lab_role)
        print(existing_lab_role, hpf.get_lab_group(ctx.guild, group), sep='\t')
        await update_previous_lab_groups_permission(existing_lab_role, hpf.get_lab_group(ctx.guild, group), deny_mask=mask)

"""
####################################################################
##################### CALL-FOR-HELP FUNCTIONS #######################
####################################################################
"""

def get_available_members_from_role(role: discord.Role) -> List[discord.Member]:
    if not role:
        return []
    online_role_members = [member for member in role.members if member.status == discord.Status.online]
    available_members = []
    for member in online_role_members:
        member_roles = member.roles
        available = True
        for role in member_roles:
            if re.search("member-group\s+[0-9]+", role.name):
                available = False
                break
        if available:
            available_members.append(member)
    return available_members

def get_teaching_team_roles(guild: discord.Guild) -> List[discord.Role]:
    return list(filter(lambda r: r.name in [PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME], guild.roles))

def get_teaching_team_members(guild: discord.Guild) -> List[discord.Member]:
    TT_roles = get_teaching_team_roles(guild)
    available_team = []
    for role in TT_roles:
        available_team.extend(get_available_members_from_role(role))
    return available_team


async def go_for_help(member: discord.Member, lab_group: discord.CategoryChannel, group: int):
    text_channel_name = hpf.get_text_channel_name(group)
    text_channel = discord.utils.get(lab_group.channels, name=text_channel_name)
    if text_channel:
        await text_channel.send(btm.message_help_on_the_way(member))
    voice_channel_name = hpf.get_voice_channel_name(group)
    voice_channel = discord.utils.get(lab_group.channels, name=voice_channel_name)
    if voice_channel and member.voice and member.voice.channel:
        await member.move_to(voice_channel)

"""
####################################################################
##################### CALL-FOR-HELP COMMANDS #######################
####################################################################
"""


@bot.command(name='raise-hand', aliases=[get_unicode_emoji_from_alias('raised_hand'), 'rh'], help='Raise your virtual hand asking for any help.')
@commands.cooldown(rate=1, per=2)
@commands.has_any_role(STUDENT_ROLE_NAME)
async def raise_hand(ctx):
    member = ctx.author
    existing_lab_group = hpf.existing_member_lab_group(member)
    general_channel = discord.utils.get(member.guild.channels, name=GENERAL_CHANNEL_NAME)
    if not existing_lab_group:
        await ctx.channel.send(btm.message_member_not_in_group_for_help())
    elif ctx.channel != hpf.existing_member_lab_text_channel(member):
        await ctx.channel(btm.message_stay_in_your_seat_error(ctx.author, existing_lab_group.name))
    elif general_channel:
        online_team = get_teaching_team_members(ctx.author.guild)
        available_team = list(filter(lambda m: not hpf.existing_member_lab_group(m), online_team))
        if available_team:
            await ctx.channel.send(btm.message_asking_for_help())
            await general_channel.send(btm.message_call_for_help(existing_lab_group.name, available_team))
        elif online_team:
            await ctx.channel.send(btm.message_no_one_available_error())
            await general_channel.send(btm.message_call_for_help(existing_lab_group.name, online_team))
        else:
            await ctx.channel.send(btm.message_no_one_online_error())
    else:
        await ctx.channel.send(btm.message_can_not_get_help_error())


"""
####################################################################
############################### MISC ###############################
####################################################################
"""


# @bot.command(name='99', help='Responds with a random quote from Brooklyn 99')
async def nine_nine(ctx):
    brooklyn_99_quotes = [
        'I\'m the human form of the 💯 emoji.',
        'Bingpot!',
        (
            'Cool. Cool cool cool cool cool cool cool, '
            'no doubt no doubt no doubt no doubt.'
        ),
    ]

    response = random.choice(brooklyn_99_quotes)
    await ctx.send(response)

@bot.command(name='roll_dice', help='Simulates rolling dice.')
@commands.cooldown(rate=1, per=1)
async def roll(ctx, number_of_dice: int=1, number_of_sides: int=6):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))

@bot.command(name='salute', help='Say hello to this friendly bot.')
@commands.cooldown(rate=1, per=1)
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