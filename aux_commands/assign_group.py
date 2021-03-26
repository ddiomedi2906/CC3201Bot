from typing import List, Dict

import random
import discord

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

async def aux_assign_all(ctx):
    print('Assigning students to open groups automatically')
    # Get number of members per group
    size_to_group = await map_size_of_members_to_group(ctx.guild)
    largest_size = max(size_to_group)
    max_group_size = GUILD_CONFIG.max_students_per_group(ctx.guild)

    no_group_students = hpf.all_students_with_no_group(ctx.guild)
    print(str(len(no_group_students))+' students are without a group')
    online_no_group_students = hpf.select_online_members(ctx.guild, no_group_students)
    # online_no_group_students = no_group_students   # ... for debugging late at night
    print(str(len(online_no_group_students))+' students are online without a group')

    online_no_group_students_with_nick = []
    for student in online_no_group_students:
        if not student.nick:
            await ctx.send(btm.message_member_need_name_error(student))
        else:
            online_no_group_students_with_nick.append(student)

    print(str(len(online_no_group_students_with_nick))+' students are online without a group but have a nick')

    if not online_no_group_students_with_nick:
        await ctx.send("There are no online students with a nickname and without a group to assign.")
        return


    await ctx.send('Assigning '+str(len(online_no_group_students_with_nick))+' online students with a nickname and without a group.')

    print('Shuffling students')
    random.shuffle(online_no_group_students_with_nick)

    for i in range(1,max_group_size):
        added_member = []
        groups = size_to_group.get(i)
        print('Processing existing groups of size '+str(i))
        if not groups is None:
            for group in groups:
                group_num = hpf.get_lab_group_number(group.name)
                print('Processing group '+group.name+' num '+str(group_num))
                if online_no_group_students_with_nick:
                    member = online_no_group_students_with_nick.pop(0)
                    print('Assigning student '+member.nick)
                    success = await aux_join_group(ctx, member, group_num)
                    if success:
                        added_member.append(group)
                    else:
                        ctx.send('Unknown error adding '+member.nick)
                else:
                    return
                # else skip member for now
            print('Updating group sizes')
            next_group = size_to_group.get(i+1)
            if next_group is None:
                next_group = []
                size_to_group[i+1] = next_group
            for group in added_member:
                groups.remove(group)
                if i < max_group_size:
                    next_group.append(group)

    print('Processing empty groups')
    empty_groups = size_to_group.get(0)
    print(str(len(empty_groups))+' empty groups exist')
    while online_no_group_students_with_nick:
        print('Moving to next empty group')
        if empty_groups is None or not empty_groups:
            empty_group = await aux_create_group(ctx)
            print('Created new empty group')
        else:
            empty_group = empty_groups.pop(0)
            print('Reusing existing empty group')
        empty_group_num = hpf.get_lab_group_number(empty_group.name)
        print('Empty group number is '+str(empty_group_num))
        for i in range(max_group_size):
            if not online_no_group_students_with_nick:
                break
            print('Adding member '+str(i+1)+' to group '+str(empty_group_num))
            member = online_no_group_students_with_nick.pop(0)
            print('Left to assign '+str(len(online_no_group_students_with_nick)))
            await aux_join_group(ctx, member, empty_group_num)
            # avoid having a group with 1 if possible
            if (len(online_no_group_students_with_nick) == 2 and max_group_size-(i+1) < 2):
                print('Skipping to ensure at least 2 members in each group')
                break

    print('Finished assignment')

async def map_size_of_members_to_group(guild: discord.Guild) -> Dict[int, List[discord.CategoryChannel]]:
    print('Getting num of members per group')
    size_to_group = {}
    print('Created dictionary')
    for group in hpf.all_existing_lab_groups(guild):
        print('Processing group '+group.name)
        group_num = hpf.get_lab_group_number(group.name)
        if is_open_group(guild, group):
            size = len(hpf.all_students_in_group(guild, group_num))
            print('The group is open and it has '+str(size)+" members")
            groups = size_to_group.get(size);
            if groups is None:
                groups = []
                size_to_group[size] = groups
            groups.append(group)
    print('Done. The dictionary: '+str(size_to_group))
    return size_to_group
