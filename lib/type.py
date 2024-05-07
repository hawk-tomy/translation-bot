from __future__ import annotations

from typing import Literal, TypeGuard, get_args

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

valid_locale_strings: tuple[LocaleString, ...] = get_args(LocaleString)


def is_valid_locale(locale: str) -> TypeGuard[LocaleString]:
    return locale in valid_locale_strings