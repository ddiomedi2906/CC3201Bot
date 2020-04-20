import json
from asyncio import Lock
from collections.abc import MutableMapping
import os
from typing import List, Dict

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

config_lock = Lock()

class GuildConfig:

    def __init__(self, config_json: str):
        self.config_json = config_json
        with open(self.config_json) as inJsonFile:
            data = json.load(inJsonFile)
        self.backup_data = data
        self.config = {}
        for guild_id, values in data.items():
            self.config[int(guild_id)] = GuildDict(values.items())
            if "OPEN_GROUPS" not in self.config[int(guild_id)]:
                self.config[int(guild_id)]["OPEN_GROUPS"] = set()
            else:
                self.config[int(guild_id)]["OPEN_GROUPS"] = set(self.config[int(guild_id)]["OPEN_GROUPS"])
            if "CLOSED_GROUPS" not in self.config[int(guild_id)]:
                self.config[int(guild_id)]["CLOSED_GROUPS"] = set()
            else:
                self.config[int(guild_id)]["CLOSED_GROUPS"] = set(self.config[int(guild_id)]["CLOSED_GROUPS"])

    @property
    def guilds(self) -> List[int]:
        return list(self.config.keys())

    def __getitem__(self, guild: discord.Guild) -> GuildDict:
        return self.config[guild.id]

    def __contains__(self, guild: discord.Guild) -> bool:
        return guild.id in self.config

    def _serialize_guild_dict(self, guild_dict: GuildDict) -> Dict:
        serialized_dict = {}
        for key, value in guild_dict.items():
            serialized_dict[key] = list(value) if type(value) == set else value
        return serialized_dict

    async def init_guild_config(self, guild: discord.Guild):
        if guild not in self:
            self.config[int(guild.id)] = GuildDict()
            await self.save(guild)

    async def save(self, guild) -> bool:
        async with config_lock:
            try:
                with open(self.config_json) as inJsonFile:
                    data = json.load(inJsonFile)
            except IOError:
                return False
            data[str(guild.id)] = self._serialize_guild_dict(self.config[guild.id])
            with open(self.config_json, "w") as outJsonFile:
                try:
                    json.dump(data, outJsonFile, indent=2)
                except TypeError:
                    json.dump(self.backup_data, outJsonFile, indent=2)
                    return False
            return True


    async def save_all(self) -> bool:
        async with config_lock:
            with open(self.config_json, "w") as outJsonFile:
                serialized_guild_config = {}
                for guild_id, guild_dict in self.config.items():
                    serialized_guild_config[guild_id] = self._serialize_guild_dict(guild_dict)
                try:
                    json.dump(serialized_guild_config, outJsonFile, indent=2)
                    self.backup_data = serialized_guild_config
                    return True
                except TypeError:
                    json.dump(self.backup_data, outJsonFile, indent=2)
            return False




PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
PROJECT_CONFIG = os.path.join(PROJECT_ROOT, 'config.json')
GUILD_CONFIG = GuildConfig(PROJECT_CONFIG)