from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from discord import Colour, Embed, Interaction, Message
from discord.app_commands import allowed_contexts, allowed_installs, command, context_menu
from discord.ext import commands

from .client import Client, UnexpectedCondition
from .localization import (
    MSG_COMMAND_DESCRIPTION_USAGE,
    MSG_COMMAND_NAME_TRANSLATE,
    MSG_COMMAND_NAME_USAGE,
    MSG_USAGE_EMBED_TITLE,
    translate as translate_static,
)
from .setting import Setting
from .string_pair import MessageData, StringPair

if TYPE_CHECKING:
    from bot import Bot

logger = getLogger(__name__)


class Translator(commands.Cog):
    def __init__(self, bot: Bot, api_client: Client) -> None:
        super().__init__()
        self.api_client = api_client
        self.bot = bot
        self.setting.cog = self

    async def cog_load(self) -> None:
        self.translate_instance = self.translate_wrapper()
        self.bot.tree.add_command(self.translate_instance)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.translate_instance.name)

    async def sender(self, interaction: Interaction, msg: MessageData) -> None:
        ephemeral = not interaction.context.dm_channel
        await interaction.followup.send(content=msg.content or '', embeds=msg.embeds, ephemeral=ephemeral)

    def translate_wrapper(self):
        @context_menu(name=MSG_COMMAND_NAME_TRANSLATE)
        @allowed_contexts(guilds=True, dms=True, private_channels=True)
        @allowed_installs(guilds=False, users=True)
        async def translate(interaction: Interaction, message: Message):
            await interaction.response.defer(ephemeral=True)
            user_id = interaction.user.id
            ephemeral = not interaction.context.dm_channel

            try:
                msgs = await self.api_client.translate(user_id, StringPair(message))
            except UnexpectedCondition as e:
                await interaction.followup.send(content=await translate_static(interaction, e.msg), ephemeral=ephemeral)
                return

            for msg in msgs:
                await interaction.followup.send(content=msg.content or '', embeds=msg.embeds, ephemeral=ephemeral)

        return translate

    @command(name=MSG_COMMAND_NAME_USAGE, description=MSG_COMMAND_DESCRIPTION_USAGE)
    @allowed_contexts(guilds=True, dms=True, private_channels=True)
    @allowed_installs(guilds=False, users=True)
    async def usage(self, interaction: Interaction):
        """show amount of usage."""
        await interaction.response.defer(ephemeral=True)
        ephemeral = not interaction.context.dm_channel
        user_id = interaction.user.id

        try:
            data = await self.api_client.fetch_usage(user_id)
        except UnexpectedCondition as e:
            await interaction.followup.send(content=await translate_static(interaction, e.msg), ephemeral=ephemeral)
            return

        embed = Embed(title=await translate_static(interaction, MSG_USAGE_EMBED_TITLE), colour=Colour.blue())
        for name, value in data:
            embed.add_field(name=name, value=value)
        await interaction.followup.send(embeds=[embed], ephemeral=ephemeral)

    setting = Setting()
