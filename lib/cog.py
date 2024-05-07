from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from discord import Interaction, Message, SelectOption
from discord.app_commands import allowed_contexts, allowed_installs, command, context_menu
from discord.ext.commands import Cog
from discord.ext.flow import (
    Button,
    Controller,
    Message as MessageData,
    ModalConfig,
    ModelBase,
    Result,
    Select,
    TextInput,
    send_modal,
)

from .client import Client, DBClient, UserInfo, is_free_user, valid_locale_strings
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


class SettingModel(ModelBase):
    def __init__(self, bot: Bot, db: DBClient, user_id: int):
        self.bot = bot
        self.db = db
        self.user_id = user_id
        self.do_insert = False

    async def before_invoke(self):
        user_info = await self.db.get_user_info(self.user_id)
        if user_info is None:
            self.do_insert = True
            user_info = UserInfo(self.user_id, None, None)
        self.user_info = user_info

    @property
    def locale_string(self):
        return 'NOT SET' if self.user_info.target_locale is None else self.user_info.target_locale

    def message(self) -> MessageData:
        has_token = (
            'NOT SET'
            if self.user_info.token is None
            else 'API Free user token'
            if is_free_user(self.user_info.token)
            else 'API Pro user token'
        )

        return MessageData(
            content='\n'.join(
                (
                    '## setting',
                    f'- token: {has_token}',
                    f'- target locale: {self.locale_string}',
                    '',
                    'if you want to save changes, please click the finish button.',
                )
            ),
            items=[
                Button(callback=self.token_button, label='set token'),
                Button(callback=self.locale_button, label='set locale'),
                Button(callback=self.finish_button, label='finish'),
            ],
        )

    async def token_button(self, interaction: Interaction):
        texts, interaction = await send_modal(
            interaction,
            ModalConfig(title='your DeepL token'),
            [TextInput(label='token', placeholder='your DeepL token.', default=self.user_info.token or '')],
        )
        assert len(texts) == 1
        token = texts[0]

        self.user_info = self.user_info._replace(token=token)
        return Result.send_message(self.message())

    async def locale_button(self, interaction: Interaction):
        def select_callback(interaction: Interaction, locales: list[str]):
            assert len(locales) == 1
            locale = locales[0]
            self.user_info = self.user_info._replace(target_locale=locale)
            return Result.send_message(self.message())

        detected_locale = await self.bot.api_client.detect_user_locale(interaction.user.id, interaction.locale)
        select = Select(
            callback=select_callback,
            options=[
                SelectOption(
                    label=locale,
                    value=locale,
                    default=detected_locale is not None and detected_locale == locale,
                )
                for locale in valid_locale_strings
            ],
            min_values=1,
            max_values=1,
        )

        return Result.send_message(
            MessageData(
                content='\n'.join(
                    (
                        f'now target locale is `{self.locale_string}`. ',
                        'you can choose target locale from below.',
                    )
                ),
                items=[select],
            )
        )

    async def finish_button(self, interaction: Interaction):
        if self.do_insert:
            await self.db.set_user_info(self.user_info)
        else:
            await self.db.update_user_info(self.user_info)
        return Result.send_message(
            MessageData(
                content='your setting has been saved!',
            )
        )


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
        @context_menu()
        @allowed_contexts(guilds=True, dms=True, private_channels=True)
        @allowed_installs(guilds=False, users=True)  # type: ignore[reportUntypedFunctionDecorator]
        async def translate(interaction: Interaction, msg: Message):
            user_id = interaction.user.id
            await Controller(ProxyModel(await self.api_client.translate(user_id, StringPair(msg)))).invoke(interaction)

        return translate

    @command()
    @allowed_contexts(guilds=False, dms=True, private_channels=False)
    @allowed_installs(guilds=False, users=True)  # type: ignore[reportUntypedFunctionDecorator]
    async def usage(self, interaction: Interaction):
        """show amount of usage"""
        user_id = interaction.user.id
        await Controller(ProxyModel(await self.api_client.fetch_usage(user_id))).invoke(interaction)

    @command()
    @allowed_contexts(guilds=False, dms=True, private_channels=False)
    @allowed_installs(guilds=False, users=True)  # type: ignore[reportUntypedFunctionDecorator]
    async def setting(self, interaction: Interaction):
        """setting of token and target locale"""
        async with self.api_client.db() as db:
            user_id = interaction.user.id
            await Controller(SettingModel(self.bot, db, user_id)).invoke(interaction)
