import re
from typing import Union, Optional

from utils import helper_functions as hpf, bot_messages as btm


def aux_get_group_members(ctx, group: Union[int, str], show_empty_error_message: bool = True) -> Optional[str]:
    group = int(re.sub(r"Group[\s]+([0-9]+)", r"\1", group)) if type(group) == str else group
    guild = ctx.guild
    existing_role = hpf.get_lab_role(guild, group)
    if not existing_role:
        return btm.message_group_not_exists_error(group)
    elif not existing_role.members and show_empty_error_message:
        return btm.message_no_members()
    elif existing_role.members:
        return btm.message_list_group_members(group, existing_role.members)
    else:
        return None


async def aux_send_list_by_chunks(ctx, message_size: int = 200):
    existing_lab_groups = hpf.all_existing_lab_groups(ctx.guild)
    if not existing_lab_groups:
        await ctx.send(btm.message_no_groups())
    else:
        message_list = []
        message_acc = "Lab list:"
        for lab_group in sorted(existing_lab_groups, key=lambda g: g.name):
            message = aux_get_group_members(ctx, lab_group.name, show_empty_error_message=False)
            if message and len(message_acc) + len(message) <= message_size:
                message_acc += '\n' + message
            elif message:
                message_list.append(message_acc)
                message_acc = '\n' + message
        message_list.append(message_acc)
        if existing_lab_groups:
            for message in message_list:
                await ctx.send(message)