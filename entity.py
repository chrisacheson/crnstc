from typing import Tuple
from dataclasses import dataclass


@dataclass
class Entity:
    x: int
    y: int
    char: str
    color: Tuple[int, int, int]

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy
