import json
from asyncio import Lock
from collections import deque
from collections.abc import MutableMapping
import os
from typing import List, Dict, Tuple, Optional

import discord

from global_variables import DEFAULT_ENV_VALUES

config_lock = Lock()


class HelpQueue:
    def __init__(self, cached_queue: List[Tuple[int, int]]):
        self.group_queue = deque()
        self.map_group_to_message_id = {}
        for group, message_id in cached_queue:
            self.group_queue.append(group)
            self.map_group_to_message_id[group] = message_id

    def size(self) -> int:
        return len(self.group_queue)

    def serialize(self) -> List[Tuple[int, int]]:
        return [(group, self.map_group_to_message_id[group]) for group in list(self.group_queue)]

    def index(self, idx: int) -> Optional[int]:
        try:
            return self.group_queue.index(idx)
        except ValueError:
            return None

    def extract_group(self, group: int) -> Optional[int]:
        try:
            self.group_queue.remove(group)
            message_id = self.map_group_to_message_id[group]
            del self.map_group_to_message_id[group]
            return message_id
        except ValueError:
            return None

    def next(self) -> Tuple[Optional[int], Optional[int]]:
        if not self.group_queue:
            return None, None
        next_group = self.group_queue.popleft()
        message_id = self.map_group_to_message_id[next_group]
        del self.map_group_to_message_id[next_group]
        return next_group, message_id

    def add(self, group: int, message_id: int) -> bool:
        if group in self:
            return False
        self.group_queue.append(group)
        self.map_group_to_message_id[group] = message_id
        return True

    def __contains__(self, next_group: int) -> bool:
        return next_group in self.map_group_to_message_id


class GroupInviteList:
    def __init__(self, cached_invitations: Dict[int, List[int]]):
        self.invitations = {member_id: set(groups) for member_id, groups in cached_invitations.items()}

    def has_invite(self, member_id: int, group: int) -> bool:
        return member_id in self.invitations and group in self.invitations[member_id]

    def add_invite(self, member_id: int, group: int):
        if member_id not in self.invitations:
            self.invitations[member_id] = set()
        self.invitations[member_id].add(group)

    def remove_invite(self, member_id: int, group: int):
        if member_id in self.invitations:
            self.invitations[member_id].remove(group)

    def clear_invites(self, member_id: int):
        if member_id in self.invitations:
            del self.invitations[member_id]

    def retrieve_invites(self, member_id: int) -> List[int]:
        if member_id not in self.invitations:
            return []
        invites = list(self.invitations[member_id])
        del self.invitations[member_id]
        return invites

    def serialize(self) -> Dict[int, List[int]]:
        return {member_id: list(groups) for member_id, groups in self.invitations.items()}


class GuildDict(MutableMapping):
    """A dictionary that applies an arbitrary key-altering
       function before accessing the keys"""

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys
        self["OPEN_GROUPS"] = set(self.store["OPEN_GROUPS"] if "OPEN_GROUPS" in self.store else [])
        self["CLOSED_GROUPS"] = set(self.store["CLOSED_GROUPS"] if "CLOSED_GROUPS" in self.store else [])
        self["GROUP_INVITES"] = GroupInviteList(self.store["GROUP_INVITES"] if "GROUP_INVITES" in self.store else {})
        self["HELP_QUEUE"] = HelpQueue(self.store["HELP_QUEUE"] if "HELP_QUEUE" in self.store else [])

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

    def serialize(self) -> Dict:
        serialized_dict = {}
        for key, value in self.store.items():
            if type(value) == set:
                serialized_dict[key] = list(value)
            elif isinstance(value, HelpQueue) or isinstance(value, GroupInviteList):
                serialized_dict[key] = value.serialize()
            else:
                serialized_dict[key] = value
        return serialized_dict


class GuildConfig:

    def __init__(self, config_json: str):
        self.config_json = config_json
        with open(self.config_json) as inJsonFile:
            data = json.load(inJsonFile)
        self.backup_data = data
        self.config = {}
        for guild_id, values in data.items():
            self.config[int(guild_id)] = GuildDict(values.items())

    @property
    def guilds(self) -> List[int]:
        return list(self.config.keys())

    def __getitem__(self, guild: discord.Guild) -> GuildDict:
        return self.config[guild.id]

    def __contains__(self, guild: discord.Guild) -> bool:
        return guild.id in self.config

    def broadcast_to_empty_groups(self, guild: discord.Guild) -> HelpQueue:
        return self.config[guild.id]["BROADCAST_TO_EMPTY_GROUPS"]

    def help_queue(self, guild: discord.Guild) -> HelpQueue:
        return self.config[guild.id]["HELP_QUEUE"]

    def group_invites(self, guild: discord.Guild) -> GroupInviteList:
        return self.config[guild.id]["GROUP_INVITES"]

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
            data[str(guild.id)] = self.config[guild.id].serialize()
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
                    serialized_guild_config[guild_id] = self.config[guild_id].serialize()
                try:
                    json.dump(serialized_guild_config, outJsonFile, indent=2)
                    self.backup_data = serialized_guild_config
                    return True
                except TypeError:
                    json.dump(self.backup_data, outJsonFile, indent=2)
            return False


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
PROJECT_CONFIG = os.path.join(PROJECT_ROOT, 'config.json')
if not os.path.isfile(PROJECT_CONFIG):
    with open(PROJECT_CONFIG, "w") as outJsonFile:
        json.dump({}, outJsonFile, indent=2)
GUILD_CONFIG = GuildConfig(PROJECT_CONFIG)
