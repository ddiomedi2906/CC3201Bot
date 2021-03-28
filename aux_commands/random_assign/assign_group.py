from typing import List, Dict, Tuple

import math
import random
import discord

from collections import deque

from aux_commands.create_delete_group import aux_create_group
from aux_commands.join_leave_group import aux_join_group
from aux_commands.open_close_groups import is_open_group
from utils import bot_messages as btm, helper_functions as hpf
from utils.guild_config import GUILD_CONFIG

"""
####################################################################
#################### ASSIGN GROUP FUNCTIONS ########################
####################################################################
"""


class RandomGroupAssigner:
    @staticmethod
    async def aux_assign_all(ctx):
        print('Assigning students to open groups automatically')
        guild = ctx.guild
        # Get number of members per group
        max_group_size = GUILD_CONFIG.max_students_per_group(guild)
        available_spots, size_to_group = await RandomGroupAssigner.map_size_of_members_to_group(guild)

        # filter non eligible students (non online or without nickname when required)
        no_group_students = hpf.all_students_with_no_group(guild)
        print(f'{len(no_group_students)} students are without a group')
        online_no_group_students = hpf.select_online_members(guild, no_group_students)
        print(f'{len(online_no_group_students)} students are online without a group')
        eligible_students = list()
        # perform nickname filtering only if nickname is required in the server
        if GUILD_CONFIG.require_nickname(guild):
            for student in online_no_group_students:
                if not student.nick:
                    await ctx.send(btm.message_member_need_name_error(student))
                else:
                    eligible_students.append(student)
            print(f'{len(eligible_students)} students are online without a group but have a nick')
        else:
            print(f'{len(eligible_students)} students are online without a group (and don\'t require a nick)')

        if not eligible_students:
            await ctx.send("There are no online students without a group to assign.")
            return

        await ctx.send(f'Assigning {len(eligible_students)} online students with a nickname and without a group.')

        # adding or trimming number of empty groups required according to the available spots in open groups
        size_to_group[0] = await RandomGroupAssigner.compute_number_of_extra_empty_groups(
            available_spots=available_spots,
            num_students=len(eligible_students),
            max_group_size=max_group_size,
            current_empty_groups=size_to_group[0]
        )

        # Start random group assignation: first we shuffle students and then start looking into groups
        print('Shuffling students')
        random.shuffle(online_no_group_students)
        for size_idx in range(max_group_size):
            groups = size_to_group.setdefault(size_idx, deque())
            print(f'Processing existing groups of size {size_idx}')
            # while we have remaining groups of size {size_idx}
            while groups:
                group = groups.popleft()
                group_num = hpf.get_lab_group_number(group.name)
                print(f'Processing group {group.name}, num {group_num}')
                # join_group sometimes fails so in this loop we make sure
                # a student is being successfully added to the group
                success = False
                while not success and eligible_students:
                    member = eligible_students.pop()
                    print(f'Assigning student {hpf.get_nick(member)}')
                    success = await aux_join_group(ctx, member, group_num)
                    if not success:
                        ctx.send(f'Unknown error adding {hpf.get_nick(member)}')
                # no more students to assign group
                if not eligible_students:
                    print('Finished assignment')
                    return
                print('Updating group sizes')
                # move group to the queue of group with size {size_idx + 1]
                next_group = size_to_group.setdefault(size_idx + 1, deque())
                next_group.append(group)
        print('Finished assignment')

    @staticmethod
    def map_size_of_members_to_group(guild: discord.Guild) -> Tuple[int, Dict[int, deque[discord.CategoryChannel]]]:
        """
        Return a {group_size} -> {queue of groups} mapping for the given Guild,
        and the number of available spots in open groups. It only considers open groups with size
        less than the maximum number of students allowed per group (set in guild config).
        """
        # Getting num of members per group
        size_to_group = dict()
        available_spots = 0
        max_group_size = GUILD_CONFIG.max_students_per_group(guild)
        for group in hpf.all_existing_lab_groups(guild):
            print(f'Processing group {group.name}...')
            group_num = hpf.get_lab_group_number(group.name)
            # if group is open and has available spots
            if is_open_group(guild, group) and size < max_group_size:
                size = len(hpf.all_students_in_group(guild, group_num))
                print(f'The group is open and it has {size} members')
                groups = size_to_group.setdefault(size, deque())
                groups.append(group)
                # only counting open groups since we use this number to measure
                # how many empty groups we will need later
                if size > 0:
                    available_spots += (max_group_size - size)
        print(f'Done. The dictionary: {size_to_group}')
        return available_spots, size_to_group

    @staticmethod
    async def compute_number_of_extra_empty_groups(
            available_spots: int,
            num_students: int,
            max_group_size: int,
            current_empty_groups: deque[discord.CategoryChannel],
    ) -> deque[discord.CategoryChannel]:
        num_students_for_empty_groups = num_students - available_spots
        num_current_empty_groups = len(current_empty_groups)
        required_empty_groups = math.ceil(num_students_for_empty_groups / max_group_size)
        # if we are missing empty groups
        if required_empty_groups > num_current_empty_groups:
            # create new groups and append them to the queue
            current_empty_groups.extend(
                await aux_create_group() for _ in range(required_empty_groups - num_current_empty_groups)
            )
        else:
            # otherwise, remove the extra empty groups
            for _ in range(num_current_empty_groups - required_empty_groups):
                current_empty_groups.popleft()
        return current_empty_groups
