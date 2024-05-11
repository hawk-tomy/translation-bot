from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, NamedTuple, Self

from asqlite import _AcquireProxyContextManager

from .type import LocaleString

if TYPE_CHECKING:
    from bot import Bot


class UserInfo(NamedTuple):
    user_id: int
    token: str | None
    target_locale: LocaleString | None

    def is_empty(self) -> bool:
        return self.token is None and self.target_locale is None


def is_free_user(token: str) -> bool:
    return token.endswith(':fx')


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
            rows = await cur.fetchone()
            if rows:
                return UserInfo(user_id, rows[0][0], rows[0][1])

        return None

    async def update_user_info(self, user_info: UserInfo) -> None:
        await self.conn.execute(
            'REPLACE INTO user (user_id, token, target_locale) VALUES (?, ?, ?)',
            (user_info.user_id, user_info.token, user_info.target_locale),
        )
