from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from discord import Interaction, Message
from discord.app_commands import allowed_contexts, allowed_installs, command, context_menu
from discord.ext.commands import Cog
from discord.ext.flow import Controller, Message as MessageData, ModelBase

from .client import Client
from .setting_model import SettingModel
from .string_pair import StringPair

if TYPE_CHECKING:
    from bot import Bot

logger = getLogger(__name__)


class ProxyModel(ModelBase):
    m: MessageData

    def __init__(self, m: MessageData):
        self.m = m

    def message(self) -> MessageData:
        return self.m


class Translator(Cog):
    def __init__(self, bot: Bot, api_client: Client) -> None:
        super().__init__()
        self.api_client = api_client
        self.bot = bot

    async def cog_load(self) -> None:
        self.translate_instance = self.translate_wrapper()
        self.bot.tree.add_command(self.translate_instance)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.translate_instance.name)

    def translate_wrapper(self):
        @context_menu()  # type: ignore[arg-type]
        @allowed_contexts(guilds=True, dms=True, private_channels=True)
        @allowed_installs(guilds=False, users=True)  # type: ignore[reportUntypedFunctionDecorator]
        async def translate(interaction: Interaction, msg: Message):
            user_id = interaction.user.id
            await Controller(ProxyModel(await self.api_client.translate(user_id, StringPair(msg)))).invoke(interaction)

        return translate

    @command()  # type: ignore[arg-type]
    @allowed_contexts(guilds=False, dms=True, private_channels=False)
    @allowed_installs(guilds=False, users=True)  # type: ignore[reportUntypedFunctionDecorator]
    async def usage(self, interaction: Interaction):
        """show amount of usage"""
        user_id = interaction.user.id
        await Controller(ProxyModel(await self.api_client.fetch_usage(user_id))).invoke(interaction)

    @command()  # type: ignore[arg-type]
    @allowed_contexts(guilds=False, dms=True, private_channels=False)
    @allowed_installs(guilds=False, users=True)  # type: ignore[reportUntypedFunctionDecorator]
    async def setting(self, interaction: Interaction):
        """setting of token and target locale"""
        async with self.api_client.db() as db:
            user_id = interaction.user.id
            await Controller(SettingModel(self.bot, db, user_id)).invoke(interaction)
