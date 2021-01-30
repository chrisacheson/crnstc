from typing import Iterable, List, Reversible, Tuple
import textwrap
from dataclasses import dataclass

import tcod

from crnstc import color
from crnstc.geometry import Rectangle


@dataclass
class Message:
    text: str
    fg: Tuple[int, int, int]

    def __post_init__(self):
        self.count = 1

    @property
    def full_text(self) -> str:
        if self.count > 1:
            return f"{self.text} (x{self.count})"

        return self.text


class MessageLog:
    def __init__(self) -> None:
        self.messages: List[Message] = []

    def add_message(self, text: str, fg: Tuple[int, int, int] = color.white, *,
                    stack: bool = True) -> None:
        if stack and self.messages and text == self.messages[-1].text:
            self.messages[-1].count += 1
        else:
            self.messages.append(Message(text, fg))

    def render(self, console: tcod.Console, shape: Rectangle) -> None:
        self.render_messages(console=console, shape=shape,
                             messages=self.messages)

    @staticmethod
    def wrap(string: str, width: int) -> Iterable[str]:
        for line in string.splitlines():
            yield from textwrap.wrap(line, width, expand_tabs=True)

    @classmethod
    def render_messages(cls, console: tcod.Console, shape: Rectangle,
                        messages: Reversible[Message]) -> None:
        y_offset = shape.h - 1

        for message in reversed(messages):
            for line in reversed(list(cls.wrap(message.full_text, shape.w))):
                text_position = shape.relative(x=0, y=y_offset)
                console.print(*text_position, string=line, fg=message.fg)
                y_offset -= 1
                if y_offset < 0:
                    return
