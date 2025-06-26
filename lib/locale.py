from __future__ import annotations

from functools import cache
from typing import Literal, TypeGuard, get_args

from discord import Interaction, Locale as DiscordLocale
from discord.app_commands import Choice, Transformer

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

valid_locale_strings: tuple[LocaleString, ...] = get_args(LocaleString.__value__)  # type: ignore[attr-defined]


def is_valid_locale(locale: str) -> TypeGuard[LocaleString]:
    return locale in valid_locale_strings


@cache
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


choice_label: dict[LocaleString, str] = {
    'AR': 'AR (العربية)',
    'BG': 'BG (български език)',
    'CS': 'CS (čeština)',
    'DA': 'DA (dansk)',
    'DE': 'DE (Deutsch)',
    'EL': 'EL (ελληνικά)',
    'EN': 'EN (English)',
    'EN-GB': 'EN-GB (English (British))',
    'EN-US': 'EN-US (English (American))',
    'ES': 'ES (español)',
    'ET': 'ET (eesti keel)',
    'FI': 'FI (suomi)',
    'FR': 'FR (français)',
    'HU': 'HU (magyar)',
    'ID': 'ID (Bahasa Indonesia)',
    'IT': 'IT (Italiano)',
    'JA': 'JA (日本語)',
    'KO': 'KO (한국어)',
    'LT': 'LT (lietuvių)',
    'LV': 'LV (latviešu)',
    'NB': 'NB (norsk bokmål)',
    'NL': 'NL (Nederlands)',
    'PL': 'PL (język polski)',
    'PT': 'PT (português)',
    'PT-BR': 'PT-BR (Português brasileiro)',
    'PT-PT': 'PT-PT (português europeu)',
    'RO': 'RO (limba )',
    'RU': 'RU (русский язык)',
    'SK': 'SK (slovenčina)',
    'SL': 'SL (slovenščina)',
    'SV': 'SV (svenska)',
    'TR': 'TR (Türkçe)',
    'UK': 'UK (українська мова)',
    'ZH': 'ZH (中文)',
}


class LocaleStringTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> LocaleString:
        if is_valid_locale(value):
            return value

        raise ValueError(f'invalid locale: {value}')

    async def autocomplete(self, interaction: Interaction, value: str) -> list[Choice[str]]:  # type: ignore[override]
        value = value.upper()

        choices: list[Choice[str]] = []
        if discord_locale := discord_locale_into_deepl_locale(interaction.locale):
            choices.append(Choice(name=choice_label[discord_locale], value=discord_locale))

        for locale in valid_locale_strings:
            if len(choices) >= 25:
                break
            if not value or value in locale:
                choice = Choice(name=choice_label[locale], value=locale)
                if choice not in choices:
                    choices.append(choice)

        return choices
