import discord

from aux_commands.create_delete_group import create_new_role
from aux_commands.open_close_groups import is_closed_group, is_open_group, open_group
from global_variables import PROFESSOR_ROLE_NAME, HEAD_TA_ROLE_NAME, TA_ROLE_NAME, STUDENT_ROLE_NAME
from utils.guild_config import GUILD_CONFIG
from utils import helper_functions as hpf, bot_messages as btm
from utils.my_converters import GuildSettings
from utils.permission_mask import PMask


async def aux_init_guild(guild: discord.Guild):
    if not guild in GUILD_CONFIG:
        return
    #print(f'{guild.name} (id: {guild.id})')
    print(guild.name)
    members = '\n - '.join([hpf.get_nick(member) for member in guild.members])
    print(f'Guild Members:\n - {members}')
    # Create or update roles
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
    # Double check existing lab groups
    for group in hpf.all_existing_lab_groups(guild):
        if not (is_open_group(guild, group) or is_closed_group(guild, group)):
            await open_group(guild, group)


async def aux_save_guild(ctx):
    if await GUILD_CONFIG.save(ctx.guild):
        await ctx.send(btm.success_guild_settings_saved(ctx.guild))
    else:
        await btm.message_unexpected_error("save")


async def aux_set_guild(ctx, settings: GuildSettings):
    guild = ctx.guild
    has_values = False
    if guild not in GUILD_CONFIG:
        await ctx.send(btm.error_guild_not_init(guild))
        print(f"Guild {guild.name} is not included on config.json!")
        return
    print(f"Setting values on guild {guild.name}...")
    for key, value in settings.changed_items:
        if value is not None:
            has_values = True
            GUILD_CONFIG[guild][key] = value
            print(f"{key}: {value}")
    if has_values:
        await ctx.send(btm.success_guild_settings_changed(guild, settings.changed_items))
