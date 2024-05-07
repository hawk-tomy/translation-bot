from __future__ import annotations

import os

from asqlite import create_pool
from discord import Intents
from discord.ext import commands

from lib import Client, Translator


class Bot(commands.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.typing = False
        super().__init__(command_prefix=commands.when_mentioned_or('/'), intents=intents)

        self.commit_hash = os.environ['COMMIT_HASH']

    async def setup_hook(self):
        self.api_client = Client(self)
        async with self.api_client.db() as db:
            await db.create_table()

        await self.add_cog(Translator(self, self.api_client))

    async def runner(self):
        async with self, create_pool(os.getenv('DATABASE_PATH', 'db/db.sqlite3')) as pool:
            self.pool = pool
            await self.start(token=os.environ['DISCORD_TOKEN'])
