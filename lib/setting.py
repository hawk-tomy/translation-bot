from __future__ import annotations

from typing import TYPE_CHECKING, Self

from discord import Interaction, ui
from discord.app_commands import Group, Transform, allowed_contexts, allowed_installs, command

from .client import Client as ApiClient, is_free_user
from .db import UserInfo
from .locale import LocaleString, LocaleStringTransformer
from .localization import (
    MSG_COMMAND_DESCRIPTION_KEY,
    MSG_COMMAND_DESCRIPTION_LOCALE,
    MSG_COMMAND_DESCRIPTION_SETTING,
    MSG_COMMAND_DESCRIPTION_SHOW,
    MSG_COMMAND_NAME_KEY,
    MSG_COMMAND_NAME_LOCALE,
    MSG_COMMAND_NAME_SETTING,
    MSG_COMMAND_NAME_SHOW,
    MSG_KEY_API_FREE,
    MSG_KEY_API_PRO,
    MSG_KEY_MODAL_LABEL,
    MSG_KEY_MODAL_PLACEHOLDER,
    MSG_KEY_MODAL_TITLE,
    MSG_KEY_SAVED,
    MSG_NOT_SET,
    MSG_SETTING_LOCALE_PLACEHOLDER,
    MSG_SETTING_SHOW_PLACEHOLDER,
    translate,
)

if TYPE_CHECKING:
    from .cog import Translator


class KeyInputModal(ui.Modal):
    key: ui.TextInput[Self] = ui.TextInput(label='key', placeholder='your DeepL key.', default='')

    def __init__(self, api_client: ApiClient, user_info: UserInfo, title: str, label: str, placeholder: str) -> None:
        super().__init__(title=title)
        self.key.label = label
        self.key.placeholder = placeholder
        self.api_client = api_client
        self.user_info = user_info

        if user_info.key is not None:
            self.key.default = user_info.key

    async def on_submit(self, interaction: Interaction) -> None:
        user_info = self.user_info._replace(key=self.key.value)
        async with self.api_client.db() as db:
            await db.update_user_info(user_info)

        ephemeral = not interaction.context.dm_channel
        await interaction.response.send_message(await translate(interaction, MSG_KEY_SAVED), ephemeral=ephemeral)


@allowed_contexts(guilds=True, dms=True, private_channels=True)
@allowed_installs(guilds=False, users=True)
class Setting(Group):
    """setting of key and target locale"""

    cog: Translator

    def __init__(self):
        super().__init__(name=MSG_COMMAND_NAME_SETTING, description=MSG_COMMAND_DESCRIPTION_SETTING)

    @property
    def api_client(self):
        return self.cog.api_client

    @command(name=MSG_COMMAND_NAME_SHOW, description=MSG_COMMAND_DESCRIPTION_SHOW)
    async def show(self, interaction: Interaction):
        """show your setting."""
        async with self.api_client.db() as db:
            user_info = await db.get_user_info(interaction.user.id)

        has_key = await translate(
            interaction,
            MSG_NOT_SET
            if user_info.key is None
            else MSG_KEY_API_FREE
            if is_free_user(user_info.key)
            else MSG_KEY_API_PRO,
        )

        locale = await translate(interaction, user_info.target_locale or MSG_NOT_SET)
        msg = await translate(interaction, MSG_SETTING_SHOW_PLACEHOLDER)
        ephemeral = not interaction.context.dm_channel
        await interaction.response.send_message(msg.format(key=has_key, locale=locale), ephemeral=ephemeral)

    @command(name=MSG_COMMAND_NAME_KEY, description=MSG_COMMAND_DESCRIPTION_KEY)
    async def key(self, interaction: Interaction):
        """set DeepL key for translation in modal."""
        async with self.api_client.db() as db:
            user_info = await db.get_user_info(interaction.user.id)
        await interaction.response.send_modal(
            KeyInputModal(
                self.api_client,
                user_info,
                title=await translate(interaction, MSG_KEY_MODAL_TITLE),
                label=await translate(interaction, MSG_KEY_MODAL_LABEL),
                placeholder=await translate(interaction, MSG_KEY_MODAL_PLACEHOLDER),
            )
        )

    @command(name=MSG_COMMAND_NAME_LOCALE, description=MSG_COMMAND_DESCRIPTION_LOCALE)
    async def locale(self, interaction: Interaction, locale: Transform[LocaleString, LocaleStringTransformer]):
        """set target locale for translation in select."""
        async with self.api_client.db() as db:
            user_info = await db.get_user_info(interaction.user.id)
            await db.update_user_info(user_info=user_info._replace(target_locale=locale))

        await interaction.response.send_message(
            (await translate(interaction, MSG_SETTING_LOCALE_PLACEHOLDER)).format(locale=locale),
            ephemeral=not interaction.context.dm_channel,
        )
