from typing import NamedTuple, Union
import math
import random
from types import SimpleNamespace

from crnstc.utils import clamp


PositionOrVector = Union["Position", "Vector"]


class Position(NamedTuple):
    x: int
    y: int

    def __add__(self, other: object) -> "Position":
        if isinstance(other, Vector):
            return Position(x=self.x + other.dx,
                            y=self.y + other.dy)
        else:
            raise TypeError

    def __sub__(self, other: PositionOrVector) -> PositionOrVector:
        if isinstance(other, Position):
            return Vector(dx=self.x - other.x,
                          dy=self.y - other.y)
        elif isinstance(other, Vector):
            return Position(x=self.x - other.dx,
                            y=self.y - other.dy)
        else:
            raise TypeError

    def distance(self, other: "Position") -> float:
        vector = self - other
        assert isinstance(vector, Vector)
        return vector.magnitude

    def relative(self, x: int, y: int) -> "Position":
        return self + Vector(dx=x, dy=y)


class Vector(NamedTuple):
    dx: int
    dy: int

    def __add__(self, other: object) -> PositionOrVector:
        if isinstance(other, Vector):
            return Vector(dx=self.dx + other.dx,
                          dy=self.dy + other.dy)
        elif isinstance(other, Position):
            return Position(x=self.dx + other.x,
                            y=self.dy + other.y)
        else:
            raise TypeError

    def __sub__(self, other: "Vector") -> "Vector":
        return Vector(dx=self.dx - other.dx,
                      dy=self.dy - other.dy)

    def __neg__(self) -> "Vector":
        return Vector(dx=-self.dx, dy=-self.dy)

    def __mul__(self, multiplier: int) -> "Vector":
        return Vector(dx=self.dx * multiplier,
                      dy=self.dy * multiplier)

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.dx ** 2 + self.dy ** 2)


compass = SimpleNamespace()

compass.north = Vector(dx=0, dy=-1)
compass.south = -compass.north
compass.east = Vector(dx=1, dy=0)
compass.west = -compass.east
compass.northeast = compass.north + compass.east
compass.northwest = compass.north + compass.west
compass.southeast = compass.south + compass.east
compass.southwest = compass.south + compass.west


class Slice2d(NamedTuple):
    x_slice: slice
    y_slice: slice


class Rectangle(NamedTuple):
    x: int
    y: int
    w: int
    h: int

    def __add__(self, other: object) -> "Rectangle":
        if isinstance(other, Vector):
            return Rectangle(x=self.x + other.dx,
                             y=self.y + other.dy,
                             w=self.w,
                             h=self.h)
        else:
            raise TypeError

    def __sub__(self, other: Vector) -> "Rectangle":
        return Rectangle(x=self.x - other.dx,
                         y=self.y - other.dy,
                         w=self.w,
                         h=self.h)

    @property
    def x2(self) -> int:
        return self.x + self.w - 1

    @property
    def y2(self) -> int:
        return self.y + self.h - 1

    @property
    def position(self) -> Position:
        return Position(x=self.x, y=self.y)

    @property
    def dimensions(self) -> Vector:
        return Vector(dx=self.w, dy=self.h)

    @property
    def center(self) -> Position:
        return Position(x=(self.x + self.x2) // 2,
                        y=(self.y + self.y2) // 2)

    @property
    def slice(self) -> Slice2d:
        return Slice2d(slice(self.x, self.x + self.w),
                       slice(self.y, self.y + self.h))

    def contains(self, position: Position) -> bool:
        return (self.x <= position.x <= self.x2
                and self.y <= position.y <= self.y2)

    def clamp(self, position: Position) -> Position:
        return Position(x=clamp(self.x, position.x, self.x2),
                        y=clamp(self.y, position.y, self.y2))

    def intersects(self, other: "Rectangle") -> bool:
        return (self.x <= other.x2
                and self.x2 >= other.x
                and self.y <= other.y2
                and self.y2 >= other.y)

    def grow(self, amount: int) -> "Rectangle":
        return Rectangle(x=self.x - amount,
                         y=self.y - amount,
                         w=self.w + 2 * amount,
                         h=self.h + 2 * amount)

    def move(self, dx: int, dy: int) -> "Rectangle":
        new_position = self.position + Vector(dx=dx, dy=dy)
        return Rectangle(*new_position, *self.dimensions)

    def resize(self, dx: int, dy: int) -> "Rectangle":
        new_dimensions = self.dimensions + Vector(dx=dx, dy=dy)
        return Rectangle(*self.position, *new_dimensions)

    def center_on(self, position: Position) -> "Rectangle":
        shift = position - self.center
        return self.move(*shift)

    def relative(self, x: int, y: int) -> Position:
        return self.position.relative(x=x, y=y)

    def random_position(self) -> Position:
        return Position(x=random.randint(self.x, self.x2),
                        y=random.randint(self.y, self.y2))

    def random_rectangle(self, min_size: Vector,
                         max_size: Vector) -> "Rectangle":
        if min_size.dx > self.w or min_size.dy > self.h:
            raise ValueError

        max_width = min(self.w, max_size.dx)
        max_height = min(self.h, max_size.dy)
        dimensions = Vector(dx=random.randint(min_size.dx, max_width),
                            dy=random.randint(min_size.dy, max_height))

        position_bounds = self.resize(*-dimensions)
        position = position_bounds.random_position()

        return Rectangle(*position, *dimensions)
