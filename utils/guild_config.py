import json
from collections.abc import MutableMapping
import os
from typing import List

import discord

from global_variables import DEFAULT_ENV_VALUES

class GuildDict(MutableMapping):
    """A dictionary that applies an arbitrary key-altering
       function before accessing the keys"""

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        key = self.__keytransform__(key)
        if key not in self.store:
            return DEFAULT_ENV_VALUES[key]
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[self.__keytransform__(key)] = value

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        return key

class GuildConfig:

    def __init__(self, config_json: str):
        self.config_json = config_json
        with open(self.config_json) as inJsonFile:
            data = json.load(inJsonFile)
        self.config = {}
        for guild_id, values in data.items():
            self.config[int(guild_id)] = GuildDict(values.items())

    def guilds(self) -> List[int]:
        return list(self.config.keys())

    def __getitem__(self, guild: discord.Guild) -> GuildDict:
        return self.config[guild.id]

    def __contains__(self, guild: discord.Guild) -> bool:
        return guild.id in self.config

    def save(self):
        with open(self.config_json, "w") as outJsonFile:
            json.dump(self.config, outJsonFile, indent=2)


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
PROJECT_CONFIG = os.path.join(PROJECT_ROOT, 'config.json')
GUILD_CONFIG = GuildConfig(PROJECT_CONFIG)