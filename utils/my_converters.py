import getopt
import re
from typing import Optional

from discord.ext import commands

from utils import bot_messages as btm, helper_functions as hpf


def convert_bool(arg: str) -> Optional[bool]:
    lowered = arg.lower()
    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off'):
        return False


class GuildSettings:
    def __init__(self, **kwargs):
        self.config = dict(kwargs.items())

    @classmethod
    async def convert(cls, ctx, argument):
        arguments = re.split('\s+', argument)
        usage = 'Usage: `!set [-n <on/off>] [-g <groups_size>]`'
        try:
            opts, args = getopt.getopt(arguments, "hn:g:", ["require_nickname=", "group_size="])
        except getopt.GetoptError:
            raise commands.BadArgument(usage)
        nickname = None
        groups_size = None
        for opt, arg in opts:
            if opt == '-h':
                break
            elif opt in ("-n", "--require_nickname"):
                nickname = convert_bool(arg)
                if nickname is None:
                    raise commands.BadArgument(usage)
            elif opt in ("-g", "--groups_size"):
                try:
                    groups_size = int(arg)
                except ValueError:
                    raise commands.BadArgument(usage)
        return cls(REQUIRE_NICKNAME=nickname, MAX_STUDENTS_PER_GROUP=groups_size)

    @property
    def changed_items(self):
        return [(key, value) for key, value in self.config.items() if value is not None]

    @property
    def unchanged_items(self):
        return [(key, value) for key, value in self.config.items() if value is None]


class LabGroup(commands.CategoryChannelConverter):
    async def convert(self, ctx, group):
        try:
            name = hpf.get_lab_group_name(int(group))
        except ValueError:
            name = group
        existing_group = hpf.get_lab_group(ctx.guild, name)
        if existing_group:
            return existing_group
        raise commands.BadArgument(btm.message_group_not_exists_error(name))