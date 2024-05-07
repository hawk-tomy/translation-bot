from __future__ import annotations

import os

from asqlite import create_pool
from discord import Intents
from discord.ext import commands


class Bot(commands.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.typing = False
        super().__init__(command_prefix=commands.when_mentioned_or('/'), intents=intents)

        self.commit_hash = os.environ['COMMIT_HASH']

    async def setup_hook(self):
        pass

    async def runner(self):
        async with self, create_pool(os.getenv('DATABASE_PATH', 'db/db.sqlite3')) as pool:
            self.pool = pool
            await self.start(token=os.environ['DISCORD_TOKEN'])
