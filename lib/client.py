from __future__ import annotations

from logging import getLogger
from sys import version
from types import TracebackType
from typing import Literal, NamedTuple, Self, TypeGuard, get_args

from aiohttp import ClientSession, __version__ as aiohttp_version
from asqlite import _AcquireProxyContextManager
from discord import Colour, Embed, Locale
from discord.ext.flow import Message as MessageData

from bot import Bot

from .string_pair import StringPair

USER_AGENT = f'personal-use discord bot. (python:{version} aiohttp:{aiohttp_version})'
logger = getLogger(__name__)

type LocaleString = Literal[
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


def is_free_user(token: str) -> bool:
    return token.endswith(':fx')


class UserInfo(NamedTuple):
    user_id: int
    token: str | None
    target_locale: LocaleString | None

    def is_empty(self) -> bool:
        return self.token is None and self.target_locale is None


class DBClient:
    def __init__(self, bot: Bot, ctx: _AcquireProxyContextManager):
        self.ctx = ctx

    async def __aenter__(self) -> Self:
        self.conn = await self.ctx.__aenter__()
        return self

    async def __aexit__(self, et: type[BaseException] | None, ev: BaseException | None, eb: TracebackType | None):
        return await self.ctx.__aexit__(et, ev, eb)

    async def create_table(self):
        await self.conn.execute(
            'CREATE TABLE IF NOT EXISTS user (user_id INT PRIMARY KEY, token TEXT, target_locale TEXT)'
        )

    async def get_user_info(self, user_id: int) -> UserInfo | None:
        async with self.conn.execute('SELECT token, target_locale FROM user WHERE user_id = ?', (user_id,)) as cur:
            rows = await cur.fetchmany()
            if rows:
                return UserInfo(user_id, rows[0][0], rows[0][1])

        await self.conn.execute('INSERT INTO user (user_id, token, target_locale) VALUES (?, NULL, NULL)', (user_id,))
        return None

    async def set_user_info(self, user_info: UserInfo) -> None:
        await self.conn.execute(
            'INSERT INTO user (user_id, token, target_locale) VALUES (?, ?, ?)',
            (user_info.user_id, user_info.token, user_info.target_locale),
        )

    async def update_user_info(self, user_info: UserInfo) -> None:
        await self.conn.execute(
            'UPDATE user SET token = ?, target_locale = ? WHERE user_id = ?',
            (user_info.token, user_info.target_locale, user_info.user_id),
        )


class Client:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

        self.free_api_session = ClientSession(base_url='https://api-free.deepl.com', headers={'User-Agent': USER_AGENT})
        self.pro_api_session = ClientSession(base_url='https://api.deepl.com', headers={'User-Agent': USER_AGENT})

    def db(self) -> DBClient:
        return DBClient(self.bot, self.pool.acquire())

    def discord_locale_into_deepl_locale(self, discord_locale: Locale) -> LocaleString | None:
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

    async def detect_user_locale(self, user_id: int, discord_locale: Locale) -> LocaleString | None:
        """Detect user's target locale from database or discord locale. This value is used as default value for locale selection.

        DO NOT USE THIS VALUE FOR TRANSLATION. RETURNED LOCALE MAYBE MISMATCHED WITH USER'S ACTUAL TARGET LOCALE.
        """
        async with self.db() as db:
            user_info = await db.get_user_info(user_id)
            if user_info is None or user_info.target_locale is None:
                return self.discord_locale_into_deepl_locale(discord_locale)
            return user_info.target_locale

    def process_status(self, status: int) -> str | None:
        if status == 200:
            return
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
            if user_info is None or user_info.is_empty():
                return MessageData(content='You should set your DeepL token and target locale first.', ephemeral=True)
            if user_info.token is None:
                return MessageData(content='You should set your DeepL token first.', ephemeral=True)
            if user_info.target_locale is None:
                return MessageData(content='You should set your target locale first.', ephemeral=True)

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
            if user_info is None or user_info.token is None:
                return MessageData(content='You should set your DeepL token first.', ephemeral=True)

        session = self.free_api_session if is_free_user(user_info.token) else self.pro_api_session
        async with session.get(
            '/v2/usage',
            headers={'Authorization': f'DeepL-Auth-Key {user_info.token}'},
        ) as res:
            msg = self.process_status(res.status)
            if msg is not None:
                return MessageData(content=msg, ephemeral=True)
            json = await res.json()

        embed = Embed(title='\u2139\ufe0f usage', colour=Colour.blue())

        for key in ('character', 'document', 'team_document'):
            if f'{key}_count' in json:
                embed.add_field(
                    name=f'{key} count',
                    value=f'{json[f"{key}_count"]}/{json[f"{key}_limit"]}',
                )
        return MessageData(embeds=[embed], ephemeral=True)
