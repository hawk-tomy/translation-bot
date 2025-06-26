from __future__ import annotations

from logging import getLogger
from sys import version
from typing import TYPE_CHECKING

from aiohttp import ClientSession, __version__ as aiohttp_version
from discord import Locale
from discord.app_commands import locale_str

from .db import DBClient, is_free_user
from .locale import LocaleString, discord_locale_into_deepl_locale
from .localization import (
    MSG_403,
    MSG_429,
    MSG_456,
    MSG_500_OR_MORE,
    MSG_NEED_KEY,
    MSG_NEED_KEY_AND_LOCALE,
    MSG_NEED_LOCALE,
    MSG_UNKNOWN_STATUS,
    MSG_USAGE_CHARACTER_COUNT,
    MSG_USAGE_DOCUMENT_COUNT,
    MSG_USAGE_TEAM_DOCUMENT_COUNT,
)
from .string_pair import StringPair

if TYPE_CHECKING:
    from bot import Bot

    from .string_pair import MessageData

USER_AGENT = f'discord translation bot (repo:https://github.com/hawk-tomy/translation-bot.git python:{version} aiohttp:{aiohttp_version})'
logger = getLogger(__name__)


class UnexpectedCondition(Exception):
    msg: locale_str

    def __init__(self, message: locale_str) -> None:
        self.msg = message


class Client:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

        self.free_api_session = ClientSession(base_url='https://api-free.deepl.com', headers={'User-Agent': USER_AGENT})
        self.pro_api_session = ClientSession(base_url='https://api.deepl.com', headers={'User-Agent': USER_AGENT})

    def db(self) -> DBClient:
        return DBClient(self.bot, self.pool.acquire())

    async def detect_user_locale(self, user_id: int, discord_locale: Locale) -> LocaleString | None:
        """Detect user's target locale from database or discord locale. This value is used as default value for locale selection.

        DO NOT USE THIS VALUE FOR TRANSLATION. RETURNED LOCALE MAYBE MISMATCHED WITH USER'S ACTUAL TARGET LOCALE.
        """
        async with self.db() as db:
            user_info = await db.get_user_info(user_id)
            if user_info.target_locale is None:
                return discord_locale_into_deepl_locale(discord_locale)
            return user_info.target_locale

    def process_status(self, status: int):
        match status:
            case 200:
                return
            case 403:
                raise UnexpectedCondition(MSG_403)
            case 456:
                raise UnexpectedCondition(MSG_456)
            case 429:
                raise UnexpectedCondition(MSG_429)
            case status if status >= 500:
                raise UnexpectedCondition(MSG_500_OR_MORE)
            case _:  # Unknown status
                raise UnexpectedCondition(MSG_UNKNOWN_STATUS)

    async def translate(self, user_id: int, pair: StringPair) -> list[MessageData]:
        async with self.db() as db:
            user_info = await db.get_user_info(user_id)
            if user_info.is_empty():
                raise UnexpectedCondition(MSG_NEED_KEY_AND_LOCALE)
            if user_info.key is None:
                raise UnexpectedCondition(MSG_NEED_KEY)
            if user_info.target_locale is None:
                raise UnexpectedCondition(MSG_NEED_LOCALE)

        k, v = zip(*pair.encode())
        session = self.free_api_session if is_free_user(user_info.key) else self.pro_api_session

        async with session.post(
            '/v2/translate',
            headers={'Authorization': f'DeepL-Auth-Key {user_info.key}'},
            params={'text': v, 'target_lang': user_info.target_locale},
        ) as resp:
            self.process_status(resp.status)
            json = await resp.json()

        return pair.decode(tuple(zip(k, (v['text'] for v in json['translations']))))

    async def fetch_usage(self, user_id: int) -> list[tuple[locale_str, str]]:
        async with self.db() as db:
            user_info = await db.get_user_info(user_id)
            if user_info.key is None:
                raise UnexpectedCondition(MSG_NEED_KEY)

        session = self.free_api_session if is_free_user(user_info.key) else self.pro_api_session
        async with session.get(
            '/v2/usage',
            headers={'Authorization': f'DeepL-Auth-Key {user_info.key}'},
        ) as res:
            self.process_status(res.status)
            json = await res.json()

        return [
            (name, f'{json[f"{key}_count"]}/{json[f"{key}_limit"]}')
            for key, name in (
                ('character', MSG_USAGE_CHARACTER_COUNT),
                ('document', MSG_USAGE_DOCUMENT_COUNT),
                ('team_document', MSG_USAGE_TEAM_DOCUMENT_COUNT),
            )
            if f'{key}_count' in json
        ]
