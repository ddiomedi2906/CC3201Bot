import discord

from aux_commands.create_delete_group import create_new_role
from utils.guild_config import GUILD_CONFIG
from utils.helper_functions import get_nick
from utils.permission_mask import PMask


async def init_guild(guild: discord.Guild):
    if not guild in GUILD_CONFIG:
        return
    PROFESSOR_ROLE_NAME = GUILD_CONFIG[guild]["PROFESSOR_ROLE_NAME"]
    HEAD_TA_ROLE_NAME = GUILD_CONFIG[guild]["HEAD_TA_ROLE_NAME"]
    TA_ROLE_NAME = GUILD_CONFIG[guild]["TA_ROLE_NAME"]
    STUDENT_ROLE_NAME = GUILD_CONFIG[guild]["STUDENT_ROLE_NAME"]
    print(f'{guild.name}(id: {guild.id})')
    members = '\n - '.join([get_nick(member) for member in guild.members])
    print(f'Guild Members:\n - {members}')
    all_allow = discord.Permissions.all()
    almost_all = discord.Permissions(PMask.ALL_BUT_ADMIN_AND_GUILD | PMask.STREAM)
    text_and_voice_allow = discord.Permissions(PMask.CHANGE_NICKNAME | PMask.PARTIAL_TEXT | PMask.PARTIAL_VOICE)
    await create_new_role(guild, PROFESSOR_ROLE_NAME, permissions=all_allow, colour=discord.Colour.blue(),
                              hoist=True, mentionable=True)
    await create_new_role(guild, HEAD_TA_ROLE_NAME, permissions=all_allow, colour=discord.Colour.red(),
                              hoist=True, mentionable=True)
    await create_new_role(guild, TA_ROLE_NAME, permissions=almost_all, colour=discord.Colour.purple(),
                              hoist=True, mentionable=True)
    await create_new_role(guild, STUDENT_ROLE_NAME, permissions=text_and_voice_allow, colour=discord.Colour.gold(),
                              hoist=True, mentionable=True)

