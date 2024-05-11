from __future__ import annotations

from logging import getLogger
from sys import version
from typing import TYPE_CHECKING

from aiohttp import ClientSession, __version__ as aiohttp_version
from discord import Colour, Embed, Locale
from discord.ext.flow import Message as MessageData

from .db import DBClient, is_free_user
from .locale import LocaleString, discord_locale_into_deepl_locale
from .string_pair import StringPair

if TYPE_CHECKING:
    from bot import Bot

USER_AGENT = f'discord translation bot (repo:https://github.com/hawk-tomy/translation-bot.git python:{version} aiohttp:{aiohttp_version})'
logger = getLogger(__name__)


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

    def process_status(self, status: int) -> str | None:
        if status == 200:
            return None
        elif status == 403:
            return 'Invalid DeepL token. Please check your token.'
        elif status == 456:
            return 'Quota exceeded. Can not translate anymore.'
        elif status == 429:
            return 'Too many requests. Please wait a moment.'
        elif status >= 500:
            return 'Internal server error. Please try again later.'
        else:  # Unknown status
            return 'Unknown error. Please try again later.'

    async def translate(self, user_id: int, pair: StringPair) -> MessageData:
        async with self.db() as db:
            user_info = await db.get_user_info(user_id)
            if user_info.is_empty():
                return MessageData(
                    content='You should set your DeepL token and target locale on DM first.',
                    ephemeral=True,
                )
            if user_info.token is None:
                return MessageData(content='You should set your DeepL token on DM first.', ephemeral=True)
            if user_info.target_locale is None:
                return MessageData(content='You should set your target locale on DM first.', ephemeral=True)

        k, v = zip(*pair.encode())
        session = self.free_api_session if is_free_user(user_info.token) else self.pro_api_session

        async with session.post(
            '/v2/translate',
            headers={'Authorization': f'DeepL-Auth-Key {user_info.token}'},
            params={'text': v, 'target_lang': user_info.target_locale},
        ) as resp:
            msg = self.process_status(resp.status)
            if msg is not None:
                return MessageData(content=msg, ephemeral=True)
            json = await resp.json()

        return pair.decode(tuple(zip(k, (v['text'] for v in json['translations']))))

    async def fetch_usage(self, user_id: int) -> MessageData:
        async with self.db() as db:
            user_info = await db.get_user_info(user_id)
            if user_info.token is None:
                return MessageData(content='You should set your DeepL token on DM first.')

        session = self.free_api_session if is_free_user(user_info.token) else self.pro_api_session
        async with session.get(
            '/v2/usage',
            headers={'Authorization': f'DeepL-Auth-Key {user_info.token}'},
        ) as res:
            msg = self.process_status(res.status)
            if msg is not None:
                return MessageData(content=msg)
            json = await res.json()

        embed = Embed(title='\u2139\ufe0f usage', colour=Colour.blue())

        for key in ('character', 'document', 'team_document'):
            if f'{key}_count' in json:
                embed.add_field(
                    name=f'{key} count',
                    value=f'{json[f"{key}_count"]}/{json[f"{key}_limit"]}',
                )
        return MessageData(embeds=[embed])
