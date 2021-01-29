from __future__ import annotations

from typing import List, TYPE_CHECKING
from dataclasses import dataclass, field

from crnstc.components.base_component import BaseComponent

if TYPE_CHECKING:
    from crnstc.entity import Actor, Item


@dataclass
class Inventory(BaseComponent):
    capacity: int
    parent: Actor = field(init=False)

    def __post_init__(self):
        self.items: List[Item] = []

    def drop(self, item: Item) -> None:
        self.items.remove(item)
        item.place(self.parent.x, self.parent.y, self.game_map)

        self.engine.message_log.add_message(f"You dropped the {item.name}.")
