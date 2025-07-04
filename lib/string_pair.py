from __future__ import annotations

from logging import getLogger
from typing import NamedTuple, TYPE_CHECKING

from discord import Embed, Message

if TYPE_CHECKING:
    from typing import Any, Generator

logger = getLogger(__name__)


def split_line(string: str, num: int) -> Generator[str, Any, Any]:
    string, num = str(string), int(num)
    while True:
        if len(string) <= num:
            yield string
            return
        str1, str2 = string[:num], string[num:]
        str1_split = str1.splitlines(keepends=True)
        if len(str1_split) > 1:
            str1, str2 = ''.join(str1_split[:-1]), str1_split[-1] + str2
        yield str1
        string = str2


class MessageData(NamedTuple):
    content: str | None = None
    embeds: list[Embed] = []


class StringPair:
    content = 'content'
    embeds = 'embed'
    embeds_title = 'title'
    embeds_description = 'description'
    embeds_footer = 'footer'
    embeds_author = 'author'
    embeds_fields = 'fields'
    embeds_fields_name = 'name'
    embeds_fields_value = 'value'

    def __init__(self, msg: Message):
        self.msg = msg

    def encode(self) -> Generator[tuple[str, str], Any, Any]:
        # content, embeds
        if self.msg.content:
            yield (self.content, self.msg.content)
        if self.msg.embeds:
            for i, e in enumerate(self.msg.embeds):
                yield from self.encode_embed(i, e)

    def encode_embed(self, i: int, e: Embed) -> Generator[tuple[str, str], Any, Any]:
        if e.title:
            yield (f'{self.embeds}.{i}.{self.embeds_title}', e.title)
        if e.description:
            yield (f'{self.embeds}.{i}.{self.embeds_description}', e.description)
        for j, f in enumerate(e.fields):
            if f.name:
                yield (f'{self.embeds}.{i}.{self.embeds_fields}.{j}.{self.embeds_fields_name}', f.name)
            if f.value:
                yield (f'{self.embeds}.{i}.{self.embeds_fields}.{j}.{self.embeds_fields_value}', f.value)
        if e.footer and e.footer.text:
            yield (f'{self.embeds}.{i}.{self.embeds_footer}', e.footer.text)

    def decode(self, pair: tuple[tuple[str, str], ...]) -> list[MessageData]:
        content: str | None = None
        embeds: list[Embed] = [Embed.from_dict(e.to_dict()) for e in self.msg.embeds]
        for k, v in pair:
            if k == self.content:
                content = v
            elif k.startswith(self.embeds):
                ks = k.split('.')
                i = int(ks[1])
                while len(embeds) <= i:
                    embeds.append(Embed())
                if ks[2] == self.embeds_title:
                    embeds[i].title = v
                elif ks[2] == self.embeds_description:
                    embeds[i].description = v
                elif ks[2] == self.embeds_fields:
                    j = int(ks[3])
                    while len(embeds[i].fields) <= j:
                        embeds[i].add_field(name='', value='')
                    if ks[4] == self.embeds_fields_name:
                        embeds[i].fields[j].name = v
                    elif ks[4] == self.embeds_fields_value:
                        embeds[i].fields[j].value = v
                    else:
                        logger.warning(f'invalid key: key={k}, value={v}')
                elif ks[2] == self.embeds_footer:
                    embeds[i].set_footer(text=v)
                else:
                    logger.warning(f'invalid key: key={k}, value={v}')
            else:
                logger.warning(f'invalid key: key={k}, value={v}')
        if content is None or len(content) < 2000:
            return [MessageData(content=content, embeds=embeds)]
        contents = list(split_line(content, 2000))

        chunked_embeds: list[list[Embed]] = [[]]
        total = 0
        for e in embeds:
            if len(chunked_embeds) >= 10 or total + len(e) > 6000:
                chunked_embeds.append([])
                total = 0
            chunked_embeds[-1].append(e)
            total += len(e)

        chunked_messages = [MessageData(content=content) for content in contents]
        if chunked_messages:
            chunked_messages[-1]._replace(embeds=chunked_embeds[0])
            chunked_messages.extend(MessageData(embeds=es) for es in chunked_embeds[1:])
        else:
            chunked_messages = [MessageData(embeds=es) for es in chunked_embeds]
        return chunked_messages
