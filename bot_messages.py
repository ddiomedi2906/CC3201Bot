
# Bot's messages

def message_group_created(category_name: str, group: int) -> str:
    return f'''New **{category_name}** created! To join use the following command: `!join-group {group}`'''