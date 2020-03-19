# bot.py
import os
import random
import re
from typing import Union, Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot_messages import message_group_created

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')

bot = commands.Bot(command_prefix='!')


"""
####################################################################
############################ EVENTS ################################
####################################################################
"""

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')
    else:
        print(error)

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

"""
####################################################################
######################### GROUP COMMANDS ###########################
####################################################################
"""

async def get_category_name(number: int):
    return f"Group {number:2}"

async def get_role_name(number: int):
    return f"member-group {number:2}"

async def get_text_channel_name(number: int):
    return f"text-channel {number:2}"

async def get_voice_channel_name(number: int):
    return f"voice-channel {number:2}"

@bot.command(name='create-group', help='Create a new lab group.')
async def create_group(ctx):
    await aux_create_group(ctx)

@bot.command(name='create-many-groups', help='Create N new lab groups.')
@commands.has_role('auxiliar')
async def create_many_groups(ctx, num_groups: int):
    for _ in range(num_groups):
        await aux_create_group(ctx)

async def aux_create_group(ctx):
    guild = ctx.guild
    existing_lab_groups = list(filter(lambda c: re.search(r"Group[\s]+[0-9]+", c.name), guild.categories))
    next_num = 1
    for idx, category in enumerate(sorted(existing_lab_groups, key=lambda c: c.name), 2):
        pattern = re.compile(f"Group[\s]+{next_num}")
        if re.search(pattern, category.name) is None:
            break
        next_num = idx
    # Create new names
    new_category_name = await get_category_name(next_num)
    new_role_name = await get_role_name(next_num)
    text_channel_name = await get_text_channel_name(next_num)
    voice_channel_name = await get_voice_channel_name(next_num)
    # category = ctx.channel.category
    existing_role = discord.utils.get(guild.roles, name=new_role_name)
    existing_category = discord.utils.get(guild.categories, name=new_category_name)
    existing_text_channel = discord.utils.get(guild.channels, name=text_channel_name)
    existing_voice_channel = discord.utils.get(guild.channels, name=voice_channel_name)
    # TODO: ver caso de ejecutar comando sin que terminar otra ejecucion previa
    if not (existing_category or existing_text_channel or existing_voice_channel or existing_role):
        try:
            # Create new role
            print(f'Creating a new role: {new_role_name}')
            new_role = await guild.create_role(name=new_role_name)
            allow_role = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            allow_role = discord.PermissionOverwrite()
            # Set permissions
            # allow_default = discord.Permissions(read_messages = True)
            allow_default = discord.Permissions()
            deny = discord.Permissions.none()
            overwrites = {
                guild.default_role: discord.PermissionOverwrite.from_pair(allow_default, deny),
            }
            print(f'Creating a new category: {new_category_name}')
            new_category = await guild.create_category_channel(new_category_name , overwrites=overwrites)
            await new_category.set_permissions(new_role, overwrite=allow_role)
            # await see_permissions(new_role, new_category)
            print(f'Creating a new channels: ({text_channel_name}) and ({voice_channel_name})')
            await guild.create_text_channel(text_channel_name, category=new_category)
            await guild.create_voice_channel(voice_channel_name, category=new_category)
            await ctx.send(message_group_created(new_category_name, next_num))
        except Exception as e:
            print(e)
            await aux_delete_group(ctx, next_num)

async def see_permissions(member, channel):
    print(f'Permission of {member} in {channel}')
    for perm, value in channel.permissions_for(member):
        print(perm, value, sep='\t')
    print('-------------------------------------')


@bot.command(name='delete-group', help='Delete a lab group. Need to provide the group number.')
async def delete_group(ctx, group: Union[int, str]):
    await aux_delete_group(ctx, group)

@bot.command(name='delete-all-groups', help='Delete all lab groups.')
@commands.has_role('auxiliar')
async def delete_all_groups(ctx):
    guild = ctx.guild
    for category in guild.categories:
        if re.search(r"Group[\s]+[0-9]+", category.name):
            await aux_delete_group(ctx, category.name)

async def aux_delete_group(ctx, group: Union[int, str]):
    guild = ctx.guild
    category_name = await get_category_name(group) if type(group) == int else group
    role_name = f"member-{category_name.lower()}"
    category = discord.utils.get(guild.categories, name=category_name)
    if category:
        channels = category.channels
        for channel in channels:
            await channel.delete()
        await category.delete()
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        await role.delete()

@bot.command(name='join-group', help='Join to a group. Need to provide the group number.')
async def join_group(ctx, group: Union[int, str], member_name: Optional[str] = None):
    guild = ctx.guild
    member = discord.utils.get(guild.members, name=member_name) if member_name else ctx.author
    role_name = await get_role_name(group) if type(group) == int else group
    role = discord.utils.get(guild.roles, name=role_name)
    await member.add_roles(role)
    print(f'Role "{role}" assigned to {member}')

@bot.command(name='leave-group', help='Leave a group. Need to provide the group number.')
async def leave_group(ctx, group: Union[int, str], member_name: Optional[str] = None):
    guild = ctx.guild
    member = discord.utils.get(guild.members, name=member_name) if member_name else ctx.author
    role_name = await get_role_name(group) if type(group) == int else group
    role = discord.utils.get(guild.roles, name=role_name)
    await member.remove_roles(role)
    print(f'Role "{role}" removed to {member}')

"""
####################################################################
######################### GROUP LIST ###########################
####################################################################
"""

@bot.command(name='get-group-members', help='List all group with its members.')
@commands.has_role('auxiliar')
async def get_lab_list(ctx, group: Union[int, str]):
    guild = ctx.guild


@bot.command(name='get-lab-list', help='List all group with its members.')
@commands.has_role('auxiliar')
async def get_lab_list(ctx):
    guild = ctx.guild
    pass

@bot.command(name='get-permissions', help='Show (not in the chat) the member\'s permissinos.')
@commands.has_role('auxiliar')
async def get_permissions(ctx):
    guild = ctx.guild
    flo = discord.utils.get(guild.members, name="floflo")
    channel = ctx.channel
    print(flo)
    permission = discord.Permissions(permissions=0)
    overwrite = discord.PermissionOverwrite()
    overwrite.send_messages = False
    """    
    overwrite['send_messages'] = False
    overwrite['read_messages'] = True
    """
    # await see_permissions(guild.me, guild)
    for perm, value in guild.permissions_for(flo):
        print(perm, value, sep='\t')

"""
####################################################################
############################### MISC ###############################
####################################################################
"""

@bot.command(name='99', help='Responds with a random quote from Brooklyn 99')
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