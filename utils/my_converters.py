import getopt
import re
from typing import Optional

from discord.ext import commands


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
        print(opts)
        for opt, arg in opts:
            if opt == '-h':
                raise commands.BadArgument(usage)
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
    def items(self):
        return self.config.items()