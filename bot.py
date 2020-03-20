# bot.py
import os
import random
import re
from typing import Union, Optional, List

import discord
from discord import Role, Permissions
from discord.ext import commands
from dotenv import load_dotenv

import bot_messages
from bot_messages import message_group_created, message_unexpected_error, message_group_deleted, message_default_error, \
    message_list_group_members, message_group_not_exists_error, message_no_groups, message_no_members, \
    message_command_not_allowed, message_member_not_exists, message_member_joined_group, message_member_left_group, \
    message_call_for_help, message_mention_member_when_join_group, message_lab_group_not_exists, \
    message_asking_for_help, message_can_not_get_help_error, message_no_one_available_error

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')
PROFESSOR_ROLE_NAME = os.getenv('PROFESSOR_ROLE_NAME')
HEAD_TA_ROLE_NAME = os.getenv('AUXILIAR_ROLE_NAME')
TA_ROLE_NAME = os.getenv('ASSISTANT_ROLE_NAME')
STUDENT_ROLE_NAME = os.getenv('STUDENT_ROLE_NAME')
GENERAL_CHANNEL_NAME = os.getenv('GENERAL_CHANNEL_NAME')

bot = commands.Bot(command_prefix='!')


"""
####################################################################
############################ EVENTS ################################
####################################################################
"""


@bot.event
async def on_ready():
    # guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
    guild = discord.utils.get(bot.guilds, name=GUILD)
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )
    members = '\n - '.join([member.name for member in guild.members])
    print(f'Guild Members:\n - {members}')
    all_allow = discord.Permissions.all()
    text_and_voice_allow = discord.Permissions(66582848)
    await create_new_role(guild, PROFESSOR_ROLE_NAME, permissions=all_allow, colour=discord.Colour.blue(), mentionable=True)
    await create_new_role(guild, HEAD_TA_ROLE_NAME, permissions=all_allow, colour=discord.Colour.red(), hoist=True, mentionable=True)
    await create_new_role(guild, TA_ROLE_NAME, permissions=all_allow, colour=discord.Colour.purple(), hoist=True, mentionable=True)
    await create_new_role(guild, STUDENT_ROLE_NAME, permissions=text_and_voice_allow, colour=discord.Colour.gold(), hoist=True, mentionable=True)


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
            if member == user and member_is_available(member):
                # print(re.match(r"Group\s+(\d+)", message.content).group(1))
                group = int(re.sub(r"\*\*Group\s+(\d+).*", r"\1", message.content))
                group_name = get_lab_group_name(group)
                lab_group = discord.utils.get(user.guild.channels, name=group_name)
                await go_for_help(member, lab_group, group)
                await reaction.message.channel.send(bot_messages.message_help_on_the_way(member))
                return


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MaxConcurrencyReached):
        print(error)
        await ctx.send(f'Only {error.number} concurred invocations of this command are allowed.')
    elif isinstance(error, commands.errors.CommandOnCooldown):
        print(error)
        await ctx.send(f'You have to wait {error.retry_after}s before using this command again.')
    elif isinstance(error, commands.errors.CheckFailure):
        print(error)
        await ctx.send('You do not have the correct role for this command.')
    else:
        print(error)


"""
####################################################################
######################### HELP FUNCTIONS #####################
####################################################################
"""

def get_lab_group_name(number: int):
    return f"Group {number:2}"

def get_role_name(number: int):
    return f"member-group {number:2}"

def get_text_channel_name(number: int):
    return f"text-channel-{number}"

def get_voice_channel_name(number: int):
    return f"voice-channel {number}"

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

def member_is_available(member: discord.Member) -> bool:
    member_roles = member.roles
    for role in member_roles:
        if re.search("member-group\s+[0-9]+", role.name):
            return False
    return True


"""
####################################################################
################### CREATE/DELETE GROUP COMMANDS ###################
####################################################################
"""

async def update_previous_lab_groups_permission(role: discord.Role, category: discord.CategoryChannel):
    guild = category.guild
    existing_lab_groups = list(filter(lambda c: re.search(r"Group[\s]+[0-9]+", c.name) and c != category, guild.categories))
    default = discord.Permissions()
    only_read_and_speak = discord.Permissions(63371584)
    for lab_group in existing_lab_groups:
        await lab_group.set_permissions(role, overwrite=discord.PermissionOverwrite.from_pair(default, only_read_and_speak))


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
    new_category_name = get_lab_group_name(next_num)
    new_role_name = get_role_name(next_num)
    text_channel_name = get_text_channel_name(next_num)
    voice_channel_name = get_voice_channel_name(next_num)
    # Check if category or channels already exist
    existing_category = discord.utils.get(guild.categories, name=new_category_name)
    existing_text_channel = discord.utils.get(guild.channels, name=text_channel_name)
    existing_voice_channel = discord.utils.get(guild.channels, name=voice_channel_name)
    if not (existing_category or existing_text_channel or existing_voice_channel):
        try:
            # Create new role
            new_role = await create_new_role(guild, new_role_name, mentionable=True)
            allow_text_and_voice = discord.Permissions(66582848)
            # Set lab group permissions
            default = discord.Permissions()
            only_read_and_speak = discord.Permissions(63371584)
            overwrites = {role: discord.PermissionOverwrite.from_pair(default, only_read_and_speak) for role in guild.roles}
            overwrites[new_role] = discord.PermissionOverwrite.from_pair(allow_text_and_voice, default)
            # Create new lab group
            print(f'Creating a new category: {new_category_name}')
            new_category = await guild.create_category_channel(new_category_name , overwrites=overwrites)
            # Deny access to the lab groups created before
            await update_previous_lab_groups_permission(new_role, new_category)
            # Create new text and voice channels
            print(f'Creating a new channels: ({text_channel_name}) and ({voice_channel_name})')
            await guild.create_text_channel(text_channel_name, category=new_category)
            await guild.create_voice_channel(voice_channel_name, category=new_category)
            # Success message
            await ctx.send(message_group_created(new_category_name, next_num))
        except Exception as e:
            print(e)
            await ctx.send(message_unexpected_error("create-group"))
            await aux_delete_group(ctx, next_num, show_bot_message=False)
            raise e


@bot.command(name='create-group', help='Create a new lab group.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def create_group(ctx):
    await aux_create_group(ctx)

@bot.command(name='create-many-groups', help='Create N new lab groups.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def create_many_groups(ctx, num_groups: int):
    for _ in range(num_groups):
        await aux_create_group(ctx)


async def aux_delete_group(ctx, group: Union[int, str], show_bot_message: bool = True):
    guild = ctx.guild
    category_name = get_lab_group_name(group) if type(group) == int else group
    role_name = f"member-{category_name.lower()}"
    category = discord.utils.get(guild.categories, name=category_name)
    success = False
    if category:
        channels = category.channels
        for channel in channels:
            await channel.delete()
        await category.delete()
        success = True
    elif show_bot_message:
        await ctx.send(message_default_error())
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        await role.delete()
    if success and show_bot_message:
        await ctx.send(message_group_deleted(category_name))


@bot.command(name='delete-group', help='Delete a lab group. Need to provide the group number.')
@commands.cooldown(rate=1, per=5)
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def delete_group(ctx, group: Union[int, str]):
    await aux_delete_group(ctx, group)


@bot.command(name='delete-all-groups', help='Delete all lab groups.')
@commands.max_concurrency(number=1)
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME)
async def delete_all_groups(ctx):
    guild = ctx.guild
    for category in sorted(guild.categories, key=lambda c: c.name, reverse=True):
        if re.search(r"Group[\s]+[0-9]+", category.name):
            print(category.name)
            await aux_delete_group(ctx, category.name)

"""
####################################################################
##################### JOIN/LEAVE GROUP COMMANDS ####################
####################################################################
"""


@bot.command(name='join-group', help='Join to a group. Need to provide the group number.')
@commands.has_any_role(HEAD_TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def join_group(ctx, group: Union[int, str], member_name: Optional[str] = None):
    guild = ctx.guild
    if discord.utils.get(ctx.author.roles, name=HEAD_TA_ROLE_NAME) and member_name:
        member = discord.utils.get(guild.members, name=member_name)
    elif member_name:
        await ctx.send(message_command_not_allowed())
        return
    else:
        member = ctx.author
    if not member:
        await ctx.send(message_member_not_exists(member_name))
        return
    role_name = get_role_name(group) if type(group) == int else group
    lab_group_name = get_lab_group_name(group) if type(group) == int else group
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
        print(f'Role "{role}" assigned to {member}')
        await ctx.send(message_member_joined_group(member.name, lab_group_name))
        text_channel_name = get_text_channel_name(group) if type(group) == int else group
        text_channel = discord.utils.get(guild.channels, name=text_channel_name)
        if text_channel:
            await text_channel.send(message_mention_member_when_join_group(member, lab_group_name))
        # Move to voice channel if connected
        voice_channel_name = get_voice_channel_name(group) if type(group) == int else group
        voice_channel = discord.utils.get(guild.channels, name=voice_channel_name)
        if voice_channel and member.voice and member.voice.channel:
            await member.move_to(voice_channel)
    else:
        await ctx.send(message_lab_group_not_exists(lab_group_name))


@bot.command(name='leave-group', help='Leave a group. Need to provide the group number.')
@commands.has_any_role(HEAD_TA_ROLE_NAME, STUDENT_ROLE_NAME)
async def leave_group(ctx, group: Union[int, str], member_name: Optional[str] = None):
    guild = ctx.guild
    if discord.utils.get(ctx.author.roles, name=HEAD_TA_ROLE_NAME) and member_name:
        member = discord.utils.get(guild.members, name=member_name)
    elif member_name:
        await ctx.send(message_command_not_allowed())
        return
    else:
        member = ctx.author
    if not member:
        await ctx.send(message_member_not_exists(member_name))
        return
    role_name = get_role_name(group) if type(group) == int else group
    lab_group_name = get_lab_group_name(group) if type(group) == int else group
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        await member.remove_roles(role)
        print(f'Role "{role}" removed to {member}')
        text_channel_name = get_voice_channel_name(group) if type(group) == int else group
        text_channel = discord.utils.get(guild.channels, name=text_channel_name)
        await ctx.send(message_member_left_group(member.name, lab_group_name))
        # Disconnect from the group voice channel if connected to it
        voice_channel_name = get_voice_channel_name(group) if type(group) == int else group
        voice_channel = discord.utils.get(guild.channels, name=voice_channel_name)
        if voice_channel and member.voice and member.voice.channel == voice_channel:
            await member.move_to()
    else:
        await ctx.send(message_lab_group_not_exists(lab_group_name))

"""
####################################################################
######################### GROUP LIST ###########################
####################################################################
"""

async def aux_get_group_members(ctx, group: Union[int, str], show_empty_error_message: bool = True):
    group = int(re.sub(r"Group[\s]+([0-9]+)", r"\1", group)) if type(group) == str else group
    guild = ctx.guild
    role_name = get_role_name(group)
    existing_role = discord.utils.get(guild.roles, name=role_name)
    if not existing_role:
        await ctx.send(message_group_not_exists_error(group))
    elif not existing_role.members and show_empty_error_message:
        await ctx.send(message_no_members())
    elif existing_role.members:
        await ctx.send(message_list_group_members(group, existing_role.members))


@bot.command(name='group-members', help="List lab group's members.")
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_group_members(ctx, group: int):
    await aux_get_group_members(ctx, group)


@bot.command(name='lab-list', help='List all group with its members.')
@commands.has_any_role(PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME)
async def get_lab_list(ctx):
    guild = ctx.guild
    existing_lab_groups = list(filter(lambda c: re.search(r"Group[\s]+[0-9]+", c.name), guild.categories))
    if not existing_lab_groups:
        await ctx.send(message_no_groups())
        return
    for lab_group in sorted(existing_lab_groups, key=lambda g: g.name):
        await aux_get_group_members(ctx, lab_group.name, show_empty_error_message=False)


"""
####################################################################
##################### CALL-FOR-HELP COMMANDS #######################
####################################################################
"""

def get_available_members_from_role(role: discord.Role) -> List[discord.Member]:
    if not role:
        return []
    role_members = role.members
    available_members = []
    for member in role_members:
        member_roles = member.roles
        available = True
        for role in member_roles:
            if re.search("member-group\s+[0-9]+", role.name):
                available = False
                break
        if available:
            available_members.append(member)
    return available_members

def get_teaching_team_roles(guild):
    return list(filter(lambda r: r.name in [PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME], guild.roles))


async def ask_for_help(member: discord.Member, group_name: str, general_channel: discord.TextChannel) -> int:
    guild = member.guild
    TT_roles = get_teaching_team_roles(guild)
    available_team = []
    for role in TT_roles:
        available_team.extend(get_available_members_from_role(role))
    await general_channel.send(message_call_for_help(group_name, available_team))
    return len(available_team)


@bot.command(name='raise-hand', help='Raise your virtual hand asking for any help.')
@commands.has_any_role(STUDENT_ROLE_NAME)
async def raise_hand(ctx):
    group_role = discord.utils.find(lambda r: re.search(r"member-group\s+\d+", r.name), ctx.author.roles)
    group = int(re.sub(r"member-group\s+(\d+)", r"\1", group_role.name))
    group_name = get_lab_group_name(group)
    general_channel = discord.utils.get(ctx.author.guild.channels, name=GENERAL_CHANNEL_NAME)
    if general_channel:
        available = await ask_for_help(ctx.author, group_name, general_channel)
        if available:
            await ctx.channel.send(message_asking_for_help())
        else:
            await ctx.channel.send(message_no_one_available_error())
    else:
        await ctx.channel.send(message_can_not_get_help_error())

async def go_for_help(member: discord.Member, lab_group: discord.CategoryChannel, group: int):
    text_channel_name = get_text_channel_name(group)
    text_channel = discord.utils.get(lab_group.channels, name=text_channel_name)
    if text_channel:
        await text_channel.send(bot_messages.message_help_on_the_way(member))
    voice_channel_name = get_voice_channel_name(group)
    voice_channel = discord.utils.get(lab_group.channels, name=voice_channel_name)
    if voice_channel and member.voice and member.voice.channel:
        await member.move_to(voice_channel)


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
async def roll(ctx, number_of_dice: int, number_of_sides: int=6):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))

@bot.command(name='salute', help='Say hello to this friendly bot.')
async def salute(ctx):
    await ctx.author.create_dm()
    await ctx.author.dm_channel.send(
        f'Hi {ctx.author.name}, welcome to my Discord server!'
    )


"""
####################################################################
############################ RUN BOT ###############################
####################################################################
"""

bot.run(TOKEN)