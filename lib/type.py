from __future__ import annotations

from typing import Literal, TypeGuard

from discord import Interaction, Locale as DiscordLocale
from discord.app_commands import Transformer
from discord.app_commands.models import Choice

type LocaleString = Literal[  # type: ignore[valid-type]
    'AR',
    'BG',
    'CS',
    'DA',
    'DE',
    'EL',
    'EN',
    'EN-GB',
    'EN-US',
    'ES',
    'ET',
    'FI',
    'FR',
    'HU',
    'ID',
    'IT',
    'JA',
    'KO',
    'LT',
    'LV',
    'NB',
    'NL',
    'PL',
    'PT',
    'PT-BR',
    'PT-PT',
    'RO',
    'RU',
    'SK',
    'SL',
    'SV',
    'TR',
    'UK',
    'ZH',
]

valid_locale_strings: tuple[LocaleString, ...] = (
    'AR',
    'BG',
    'CS',
    'DA',
    'DE',
    'EL',
    'EN',
    'EN-GB',
    'EN-US',
    'ES',
    'ET',
    'FI',
    'FR',
    'HU',
    'ID',
    'IT',
    'JA',
    'KO',
    'LT',
    'LV',
    'NB',
    'NL',
    'PL',
    'PT',
    'PT-BR',
    'PT-PT',
    'RO',
    'RU',
    'SK',
    'SL',
    'SV',
    'TR',
    'UK',
    'ZH',
)


def is_valid_locale(locale: str) -> TypeGuard[LocaleString]:
    return locale in valid_locale_strings


def discord_locale_into_deepl_locale(discord_locale: DiscordLocale) -> LocaleString | None:
    """Convert discord_locale into DeepL locale. If discord_locale is not supported, return None."""
    locale = discord_locale.value.upper()
    if is_valid_locale(locale):
        return locale
    match locale:
        case 'ES-419' | 'ES-ES':
            return 'ES'
        case 'SV-SE':
            return 'SV'
        case 'ZH-CN' | 'ZH-TW':
            return 'ZH'
        case 'NO':
            return 'NB'
        case _:
            return None


class LocaleStringTransformer(Transformer):
    @property
    def min_value(self) -> int:
        return 1

    @property
    def max_value(self) -> int:
        return 1

    async def transform(self, interaction: Interaction, value: str) -> LocaleString:
        if is_valid_locale(value):
            return value

        raise ValueError(f'invalid locale: {value}')

    async def autocomplete(self, interaction: Interaction, value: str) -> list[Choice[str]]:
        value = value.upper()

        choices: list[Choice[LocaleString]] = []
        if discord_locale := discord_locale_into_deepl_locale(interaction.locale):
            choices.append(Choice(name=discord_locale, value=discord_locale))

        for locale in valid_locale_strings:
            if len(choices) >= 25:
                break
            if value:
                if value in locale:
                    choices.append(Choice(name=locale, value=locale))
                else:
                    continue
            else:
                choices.append(Choice(name=locale, value=locale))

        return choices
