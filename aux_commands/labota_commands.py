from random_assign import RandomGroupAssigner


class LabotaCommands:
    """
    Interface for all Labota commands.

    As a final goal, bot.py file should be calling only commands from this proxy class.
    """

    @staticmethod
    async def assign_all(ctx):
        """
        TODO: add function description
        """
        async with ctx.channel.typing():
            return await RandomGroupAssigner.aux_assign_all(ctx)
