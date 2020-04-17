from enum import IntFlag


class PMask(IntFlag):
    STREAM = 512
    VIEW = 1024
    CHANGE_NICKNAME = 67108864
    PARTIAL_TEXT = 129088
    PARTIAL_VOICE = 49283072
    ALL_BUT_ADMIN_AND_GUILD = 1341652291

    @classmethod
    def has_key(cls, key):
        return key in cls._member_names_