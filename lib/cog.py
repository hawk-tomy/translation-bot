from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from discord import Colour, Embed, Interaction, Message
from discord.app_commands import allowed_contexts, allowed_installs, command, context_menu
from discord.ext.commands import Cog
from discord.ext.flow import Controller, Message as MessageData, ModelBase

from .string_pair import StringPair

if TYPE_CHECKING:
    from bot import Bot

logger = getLogger(__name__)


class Model(ModelBase):
    m: MessageData

    def __init__(self, m: MessageData):
        self.m = m

    def message(self) -> MessageData:
        return self.m


class Translator(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    async def cog_load(self) -> None:
        self.translate_instance = self.translate_wrapper()
        self.bot.tree.add_command(self.translate_instance)

    async def cog_unload(self) -> None:
        await self.session.close()
        self.bot.tree.remove_command(self.translate_instance.name)

    def translate_wrapper(self):
        @context_menu()
        @allowed_contexts(guilds=True, dms=True, private_channels=True)
        @allowed_installs(guilds=False, users=True)  # type: ignore[reportUntypedFunctionDecorator]
        async def translate(interaction: Interaction, message: Message):
            encoder_decoder = StringPair(message)
            pair: tuple[tuple[str, str], ...]
            pair = tuple(encoder_decoder.encode())
            pair = await self.call_translator(pair)
            await Controller(Model(encoder_decoder.decode(pair))).invoke(interaction)

        return translate

    @command()
    @allowed_contexts(guilds=False, dms=True, private_channels=False)
    @allowed_installs(guilds=False, users=True)  # type: ignore[reportUntypedFunctionDecorator]
    async def usage(self, interaction: Interaction):
        """show amount of usage"""
        async with self.session.get('/v2/usage') as res:
            self.process_status(res.status)
            json: dict[str, int] = await res.json()
            e = Embed(
                title='\u2139\ufe0f usage',
                colour=Colour.blue(),
            )

            for k in ('character', 'document', 'team_document'):
                if f'{k}_count' in json:
                    e.add_field(
                        name=f'{k} count',
                        value=f'{json[f"{k}_count"]}/{json[f"{k}_limit"]}',
                    )
            await interaction.response.send_message(embed=e, ephemeral=True)
