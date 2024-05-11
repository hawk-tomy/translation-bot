from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Interaction, SelectOption
from discord.ext.flow import (
    Button,
    Message as MessageData,
    ModalConfig,
    ModelBase,
    Result,
    Select,
    TextInput,
    send_modal,
)

from .client import DBClient, is_free_user
from .db import UserInfo
from .type import is_valid_locale, valid_locale_strings

if TYPE_CHECKING:
    from bot import Bot


class SettingModel(ModelBase):
    def __init__(self, bot: Bot, db: DBClient, user_id: int):
        self.bot = bot
        self.db = db
        self.user_id = user_id

    async def before_invoke(self):
        self.user_info = await self.db.get_user_info(self.user_id) or UserInfo(self.user_id, None, None)

    @property
    def locale_string(self):
        return self.user_info.target_locale or 'NOT SET'

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
            edit_original=True,
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
        return Result.send_message(self.message(), interaction=interaction)

    async def locale_button(self, interaction: Interaction):
        def select_callback(interaction: Interaction, locales: list[str]):
            assert len(locales) == 1
            locale = locales[0]
            if is_valid_locale(locale):
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
                edit_original=True,
            )
        )

    async def finish_button(self, _: Interaction):
        await self.db.update_user_info(self.user_info)
        return Result.send_message(MessageData(content='your setting has been saved!', edit_original=True))
