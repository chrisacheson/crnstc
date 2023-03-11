from numbers import Number
from typing import NamedTuple


class Vector(NamedTuple):
    x: Number
    y: Number
    z: Number

    def __add__(self, other: object) -> "Vector":
        return Vector(x=self.x + other[0],
                      y=self.y + other[1],
                      z=self.z + other[2])

    def __sub__(self, other: object) -> "Vector":
        return Vector(x=self.x - other[0],
                      y=self.y - other[1],
                      z=self.z - other[2])

    def __mul__(self, other: Number) -> "Vector":
        return Vector(x=self.x * other,
                      y=self.y * other,
                      z=self.z * other)

    def __mod__(self, other: int) -> "Vector":
        return Vector(x=self.x % other,
                      y=self.y % other,
                      z=self.z % other)

    def align(self, grid_size: int) -> "Vector":
        return self - self % grid_size
