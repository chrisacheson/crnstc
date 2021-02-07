import math
import random
from types import SimpleNamespace
from typing import Iterable, List, NamedTuple, Tuple, Union

from crnstc.utils import clamp


Float2Tuple = Tuple[float, float]
Line1d2Tuple = Tuple["Line1d", "Line1d"]
Line1dIterable = Iterable["Line1d"]
Line1dList = List["Line1d"]
PositionOrVector = Union["Position", "Vector"]
PositionOrRectangle = Union["Position", "Rectangle"]
RectangleList = List["Rectangle"]
StretchyLength2Tuple = Tuple["StretchyLength", "StretchyLength"]
StretchyLengthIterable = Iterable["StretchyLength"]


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
    def lines(self) -> Line1d2Tuple:
        """
        The 1-dimensional line segments forming the sides of this rectangle, as
        a (horizontal, vertical) tuple.

        """
        return (Line1d(position=self.x, length=self.w),
                Line1d(position=self.y, length=self.h))

    @property
    def center(self) -> Position:
        return Position(x=(self.x + self.x2) // 2,
                        y=(self.y + self.y2) // 2)

    @property
    def slice(self) -> Slice2d:
        return Slice2d(slice(self.x, self.x + self.w),
                       slice(self.y, self.y + self.h))

    def contains(self, shape: PositionOrRectangle) -> bool:
        if isinstance(shape, Position):
            return (self.x <= shape.x <= self.x2
                    and self.y <= shape.y <= self.y2)
        elif isinstance(shape, Rectangle):
            return (self.contains(shape.position)
                    and self.contains(Position(x=shape.x2, y=shape.y2)))
        else:
            raise TypeError

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

    @classmethod
    def from_lines(cls, horizontal: "Line1d",
                   vertical: "Line1d") -> "Rectangle":
        """
        Construct a Rectangle from two 1-dimensional lines.

        Args:
            horizontal: The line that will form the top and bottom sides of the
                new rectangle.
            vertical: The line that will form the left and right sides of the
                new rectangle.

        Returns:
            The new Rectangle.

        """
        return cls(x=horizontal.position,
                   y=vertical.position,
                   w=horizontal.length,
                   h=vertical.length)

    @classmethod
    def multiple_from_lines(cls, horizontal: Line1dIterable,
                            vertical: Line1dIterable) -> RectangleList:
        """
        Construct Rectangle objects from pairs of 1-dimensional lines.

        Args:
            horizontal: The lines that will form the top and bottom sides of
                the new rectangles.
            vertical: The lines that will form the left and right sides of
                the new rectangles.

        Returns:
            A list of the new Rectangle objects. The order corresponds to the
            first vertical line paired with each horizontal line in order,
            followed by the second vertical line paired with the same, and so
            on.

        """
        rectangles: RectangleList = list()

        for vline in vertical:
            for hline in horizontal:
                rectangles.append(Rectangle.from_lines(horizontal=hline,
                                                       vertical=vline))

        return rectangles


class Line1d(NamedTuple):
    """
    A line segment in 1-dimensional space.

    Args:
        position: The position of the lesser endpoint of the line segment.
        length: The length of the line segment.

    """
    position: int
    length: int

    def allocate(self, stretchy_lengths: StretchyLengthIterable) -> Line1dList:
        """
        Divide the line segment into smaller segments corresponding to a
        collection of StretchyLength objects.

        Args:
            stretchy_lengths: The collection of StretchyLength objects.

        Returns:
            A list of line segments corresponding to the specified
            StretchyLength objects.

        """
        # List of calculations associated with each StretchyLength
        calcs = list()
        # How much length is left to allocate
        remaining_length: int = self.length
        # Combined expansion weight of unallocated items
        remaining_expansion: float = 0.0

        for index, stretchy in enumerate(stretchy_lengths):
            calcs.append(SimpleNamespace(
                index=index,
                stretchy=stretchy,
                length=stretchy.min_length,
            ))
            remaining_length -= stretchy.min_length
            remaining_expansion += stretchy.expansion

        if remaining_length > 0:
            # Sort items in a way that lets us do everything in one pass
            def calcs_sort_key(calc):
                # Treat zero as infinite
                max_length = calc.stretchy.max_length or math.inf
                # Items most likely to hit max_length go first
                primary = max_length / calc.stretchy.expansion
                # Among the remainder, higher expansion goes first
                secondary = -calc.stretchy.expansion
                return primary, secondary
            calcs.sort(key=calcs_sort_key)

            for calc in calcs:
                s: StretchyLength = calc.stretchy
                percentage: float = s.expansion / remaining_expansion
                add_length: int = math.ceil(remaining_length * percentage)
                max_add = (s.max_length or math.inf) - calc.length
                add_length = min(add_length, max_add)
                calc.length += add_length
                remaining_length -= add_length
                remaining_expansion -= calc.stretchy.expansion

            # Put everything back in order
            calcs.sort(key=lambda c: c.index)

        allocations: Line1dList = list()
        position = self.position

        for calc in calcs:
            allocations.append(Line1d(position=position, length=calc.length))
            position += calc.length

        return allocations


class StretchyLength(NamedTuple):
    """
    A 1-dimensional length of variable size.

    Args:
        min_length: The lower bound of the length.
        max_length: The upper bound of the length. Zero means no upper bound.
        expansion: The expansion weight of the length. Used to determine
            allocation of extra space among a collection of StretchyLength
            objects.

    """
    min_length: int
    max_length: int
    expansion: float


class StretchyArea(NamedTuple):
    """
    A rectangular area of variable size.

    Args:
        min_size: A vector representing the minimum width and height of the
            area.
        max_size: A vector representing the maximum width and height of the
            area. If either dimension is zero, that dimension has no maximum.
        expansion: The expansion weights of the area's width and height. Used
            to determine allocation of extra space among a collection of
            StretchyArea objects.

    """
    min_size: Vector = Vector(0, 0)
    max_size: Vector = Vector(0, 0)
    expansion: Float2Tuple = (1.0, 1.0)

    @property
    def stretchy_lengths(self) -> StretchyLength2Tuple:
        """
        StretchyLength objects representing this area, as a (horizontal,
        vertical) tuple.

        """
        return (
            StretchyLength(min_length=self.min_size[0],
                           max_length=self.max_size[0],
                           expansion=self.expansion[0]),
            StretchyLength(min_length=self.min_size[1],
                           max_length=self.max_size[1],
                           expansion=self.expansion[1]),
        )
