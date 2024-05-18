from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, Unpack

from discord import Interaction, Locale
from discord.app_commands import Translator, locale_str

if TYPE_CHECKING:
    from discord.app_commands import TranslationContextTypes


MSG_NEED_TOKEN = locale_str('You should set your DeepL token on DM first.')
MSG_NEED_LOCALE = locale_str('You should set your target locale on DM first.')
MSG_NEED_TOKEN_AND_LOCALE = locale_str('You should set your DeepL token and target locale on DM first.')
MSG_403 = locale_str('Invalid DeepL token. Please check your token.')
MSG_456 = locale_str('Quota exceeded. Can not translate anymore.')
MSG_429 = locale_str('Too many requests. Please wait a moment.')
MSG_500_OR_MORE = locale_str('Internal server error. Please try again later.')
MSG_UNKNOWN_STATUS = locale_str('Unknown error. Please try again later.')

MSG_COMMAND_NAME_SETTING = locale_str('setting')
MSG_COMMAND_DESCRIPTION_SETTING = locale_str('setting of token and target locale.')

MSG_COMMAND_NAME_SHOW = locale_str('show')
MSG_COMMAND_DESCRIPTION_SHOW = locale_str('show your setting.')

MSG_COMMAND_NAME_TOKEN = locale_str('token')
MSG_COMMAND_DESCRIPTION_TOKEN = locale_str('set DeepL token for translation in modal.')

MSG_COMMAND_NAME_LOCALE = locale_str('locale')
MSG_COMMAND_DESCRIPTION_LOCALE = locale_str('set target locale for translation in select.')

MSG_COMMAND_NAME_USAGE = locale_str('usage')
MSG_COMMAND_DESCRIPTION_USAGE = locale_str('show amount of usage.')

MSG_COMMAND_NAME_TRANSLATE = locale_str('translate')

MSG_NOT_SET = locale_str('NOT SET')

MSG_TOKEN_API_FREE = locale_str('Free API user token')
MSG_TOKEN_API_PRO = locale_str('Pro API user token')
MSG_TOKEN_MODAL_TITLE = locale_str('your DeepL token')
MSG_TOKEN_MODAL_LABEL = locale_str('token')
MSG_TOKEN_MODAL_PLACEHOLDER = locale_str('your DeepL token here.')
MSG_TOKEN_SAVED = locale_str('your token has been saved!')

MSG_USAGE_EMBED_TITLE = locale_str('\u2139\ufe0f usage')
MSG_USAGE_CHARACTER_COUNT = locale_str('character count')
MSG_USAGE_DOCUMENT_COUNT = locale_str('document count')
MSG_USAGE_TEAM_DOCUMENT_COUNT = locale_str('team document count')

MSG_SETTING_SHOW_PLACEHOLDER = locale_str("""
## setting
- token: {token}
- target locale: {locale}
""")
MSG_SETTING_LOCALE_PLACEHOLDER = locale_str('target locale has been set to `{locale}`.')


class _TranslateKWargs(TypedDict, total=False):
    locale: Locale
    data: Any


async def translate(interaction: Interaction, string: str | locale_str, **kwargs: Unpack[_TranslateKWargs]) -> str:
    if (msg := await interaction.translate(string, **kwargs)) is not None:
        return msg
    raise ValueError('Unreachable (failed find translation msg)')


localize_key: dict[locale_str, str] = {
    MSG_NEED_TOKEN: 'MSG_NEED_TOKEN',
    MSG_NEED_LOCALE: 'MSG_NEED_LOCALE',
    MSG_NEED_TOKEN_AND_LOCALE: 'MSG_NEED_TOKEN_AND_LOCALE',
    MSG_403: 'MSG_403',
    MSG_456: 'MSG_456',
    MSG_429: 'MSG_429',
    MSG_500_OR_MORE: 'MSG_500_OR_MORE',
    MSG_UNKNOWN_STATUS: 'MSG_UNKNOWN_STATUS',
    MSG_COMMAND_NAME_SETTING: 'MSG_COMMAND_NAME_SETTING',
    MSG_COMMAND_DESCRIPTION_SETTING: 'MSG_COMMAND_DESCRIPTION_SETTING',
    MSG_COMMAND_NAME_SHOW: 'MSG_COMMAND_NAME_SHOW',
    MSG_COMMAND_DESCRIPTION_SHOW: 'MSG_COMMAND_DESCRIPTION_SHOW',
    MSG_COMMAND_NAME_TOKEN: 'MSG_COMMAND_NAME_TOKEN',
    MSG_COMMAND_DESCRIPTION_TOKEN: 'MSG_COMMAND_DESCRIPTION_TOKEN',
    MSG_COMMAND_NAME_LOCALE: 'MSG_COMMAND_NAME_LOCALE',
    MSG_COMMAND_DESCRIPTION_LOCALE: 'MSG_COMMAND_DESCRIPTION_LOCALE',
    MSG_COMMAND_NAME_USAGE: 'MSG_COMMAND_NAME_USAGE',
    MSG_COMMAND_DESCRIPTION_USAGE: 'MSG_COMMAND_DESCRIPTION_USAGE',
    MSG_COMMAND_NAME_TRANSLATE: 'MSG_COMMAND_NAME_TRANSLATE',
    MSG_NOT_SET: 'MSG_NOT_SET',
    MSG_TOKEN_API_FREE: 'MSG_TOKEN_API_FREE',
    MSG_TOKEN_API_PRO: 'MSG_TOKEN_API_PRO',
    MSG_TOKEN_MODAL_TITLE: 'MSG_TOKEN_MODAL_TITLE',
    MSG_TOKEN_MODAL_LABEL: 'MSG_TOKEN_MODAL_LABEL',
    MSG_TOKEN_MODAL_PLACEHOLDER: 'MSG_TOKEN_MODAL_PLACEHOLDER',
    MSG_TOKEN_SAVED: 'MSG_TOKEN_SAVED',
    MSG_USAGE_EMBED_TITLE: 'MSG_USAGE_EMBED_TITLE',
    MSG_USAGE_CHARACTER_COUNT: 'MSG_USAGE_CHARACTER_COUNT',
    MSG_USAGE_DOCUMENT_COUNT: 'MSG_USAGE_DOCUMENT_COUNT',
    MSG_USAGE_TEAM_DOCUMENT_COUNT: 'MSG_USAGE_TEAM_DOCUMENT_COUNT',
    MSG_SETTING_SHOW_PLACEHOLDER: 'MSG_SETTING_SHOW_PLACEHOLDER',
    MSG_SETTING_LOCALE_PLACEHOLDER: 'MSG_SETTING_LOCALE_PLACEHOLDER',
}


class DiscordTranslator(Translator):
    data: dict[str, dict[str, str]]

    async def load(self) -> None:
        self.data = tomllib.loads((Path(__file__).parent / 'l10n.toml').read_text())

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None:
        return (
            self.data.get(locale.value, {}).get(localize_key[string]) if string in localize_key else None
        ) or string.message
