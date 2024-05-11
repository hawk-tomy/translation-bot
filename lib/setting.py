from __future__ import annotations

from typing import TYPE_CHECKING, Self

from discord import Interaction, ui
from discord.app_commands import Group, Transform, allowed_contexts, allowed_installs, command

from .client import Client as ApiClient, is_free_user
from .db import UserInfo
from .locale import LocaleString, LocaleStringTransformer

if TYPE_CHECKING:
    from .cog import Translator


class TokenInputModal(ui.Modal):
    token: ui.TextInput[Self] = ui.TextInput(label='token', placeholder='your DeepL token.', default='')

    def __init__(self, api_client: ApiClient, user_info: UserInfo) -> None:
        super().__init__(title='your DeepL token')
        self.api_client = api_client
        self.user_info = user_info

        if user_info.token is not None:
            self.token.default = user_info.token

    async def on_submit(self, interaction: Interaction) -> None:
        user_info = self.user_info._replace(token=self.token.value)
        async with self.api_client.db() as db:
            await db.update_user_info(user_info)

        await interaction.response.send_message('your token has been saved!')


@allowed_contexts(guilds=False, dms=True, private_channels=False)
@allowed_installs(guilds=False, users=True)
class Setting(Group):
    """setting of token and target locale"""

    cog: Translator

    def __init__(self):
        super().__init__(name='setting')

    @property
    def api_client(self):
        return self.cog.api_client

    @command()
    async def show(self, interaction: Interaction):
        """show your setting."""
        async with self.api_client.db() as db:
            user_info = await db.get_user_info(interaction.user.id)
        has_token = (
            'NOT SET'
            if user_info.token is None
            else f'API {'Free' if is_free_user(user_info.token) else 'Pro'} user token'
        )
        await interaction.response.send_message(
            '\n'.join(
                (
                    '## setting',
                    f'- token: {has_token}',
                    f'- target locale: {user_info.target_locale or 'NOT SET'}',
                )
            )
        )

    @command()
    async def token(self, interaction: Interaction):
        """set DeepL token for translation in modal."""
        async with self.api_client.db() as db:
            user_info = await db.get_user_info(interaction.user.id)
        await interaction.response.send_modal(TokenInputModal(self.api_client, user_info))

    @command()
    async def locale(self, interaction: Interaction, locale: Transform[LocaleString, LocaleStringTransformer]):
        """set target locale for translation in select."""
        async with self.api_client.db() as db:
            user_info = await db.get_user_info(interaction.user.id)
            await db.update_user_info(user_info=user_info._replace(target_locale=locale))

        await interaction.response.send_message(f'target locale has been set to `{locale}`.')
