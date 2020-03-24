from typing import Union, Optional

import discord

EMOJI_UNICODE_NAME = {
    'one': "1\ufe0f\u20e3",
    'slight_smile': "\U0001f642",
    'thumbsup': "\U0001f44d",
    "raised_hand": "\u270b",
    "wave": "\U0001f44b"
}

def get_unicode_emoji_from_alias(emoji_alias: str) -> Optional[str]:
    return EMOJI_UNICODE_NAME[emoji_alias] if emoji_alias in EMOJI_UNICODE_NAME else None

def get_unicode_from_emoji(emoji: Union[str, discord.Emoji]) -> str:
    """ Return escaped unicode! Do not use to compare a raw emoji """
    emoji_name = emoji if type(str) else emoji.name
    return emoji_name.encode('unicode-escape').decode('ASCII')

def same_emoji(emoji: Union[str, discord.Emoji], emoji_alias: str) -> bool:
    return emoji == get_unicode_emoji_from_alias(emoji_alias)

