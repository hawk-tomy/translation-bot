from __future__ import annotations

import asyncio
import datetime
import io
import logging
import logging.handlers
import os
import sys
import types
from pathlib import Path

import aiohttp
import discord

os.chdir(Path(__file__).resolve(strict=True).parent)
JST = datetime.timezone(datetime.timedelta(hours=9), name='JST')


class FormatterWithTZ(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None):
        return datetime.datetime.fromtimestamp(record.created).astimezone(tz=JST).isoformat()


class QueueWithAsyncFor[T](asyncio.Queue[T]):
    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.get()


class WebhookHandler(logging.Handler):
    def __init__(self, queue: QueueWithAsyncFor[str]) -> None:
        self.queue = queue
        super().__init__(level=logging.WARNING)

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        for path in sys.path:
            msg = msg.replace(path, '<import_path>')
        self.queue.put_nowait(msg)


class WebhookCtxMgr:
    def __init__(self, url: str) -> None:
        self.url = url

    async def __aenter__(self) -> discord.Webhook:
        self.__session = await aiohttp.ClientSession().__aenter__()
        self.webhook = await discord.Webhook.from_url(self.url, session=self.__session).fetch()
        return self.webhook

    async def __aexit__(self, et: type[BaseException] | None, ev: BaseException | None, eb: types.TracebackType | None):
        return await self.__session.__aexit__(et, ev, eb)


class WebhookSender:
    def __init__(self, url: str, queue: QueueWithAsyncFor[str]) -> None:
        self.url = url
        self.queue = queue

    async def run(self):
        async with WebhookCtxMgr(url=self.url) as webhook:
            async for msg in self.queue:
                if len(msg) <= 1990:
                    await self.send_msg(msg=f'```py\n{msg}```', webhook=webhook)
                else:
                    await self.send_msg(
                        file=discord.File(io.BytesIO(msg.encode('utf-8')), filename='log.txt'),
                        webhook=webhook,
                    )

    async def send_msg(self, msg: str | None = None, file: discord.File | None = None, *, webhook: discord.Webhook):
        sleep_until = 4
        while True:
            try:
                if file is None:
                    if msg is None:
                        return
                    await webhook.send(msg)
                else:
                    await webhook.send(file=file)
            except Exception:
                await asyncio.sleep(sleep_until)
                sleep_until <<= 2
            else:
                break


def setup_logging(queue: QueueWithAsyncFor[str]):
    logging.getLogger('discord').setLevel(logging.NOTSET)
    logging.getLogger('asyncio').setLevel(logging.NOTSET)
    logging.getLogger('lib').setLevel(logging.NOTSET)
    logging.getLogger('bot').setLevel(logging.NOTSET)

    log = logging.getLogger()
    log.setLevel(logging.NOTSET)

    fmt = FormatterWithTZ('{asctime};{name};{levelname};{message}', style='{')

    fh = logging.handlers.TimedRotatingFileHandler(filename='log/bot.log', encoding='utf-8', when='midnight')
    fh.setLevel(logging.NOTSET)
    fh.setFormatter(fmt)
    log.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    wh = WebhookHandler(queue)
    wh.setLevel(logging.WARNING)
    wh.setFormatter(fmt)
    log.addHandler(wh)


async def main():
    queue = QueueWithAsyncFor[str]()
    setup_logging(queue)

    from bot import Bot

    bot = Bot()
    webhook_sender = WebhookSender(url=os.environ['WEBHOOK_URL'], queue=queue)

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(bot.runner())
            tg.create_task(webhook_sender.run())
    except* Exception:
        logging.getLogger('bot').exception('Bot is finished with exception. Raised exception is:')


if __name__ == '__main__':
    asyncio.run(main(), debug=True)
