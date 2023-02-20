from typing import NamedTuple


class Vector(NamedTuple):
    x: int
    y: int
    z: int

    def __add__(self, other: "Vector") -> "Vector":
        return Vector(x=self.x + other.x,
                      y=self.y + other.y,
                      z=self.z + other.z)

    def __sub__(self, other: "Vector") -> "Vector":
        return Vector(x=self.x - other.x,
                      y=self.y - other.y,
                      z=self.z - other.z)

    def __mod__(self, other: int) -> "Vector":
        return Vector(x=self.x % other,
                      y=self.y % other,
                      z=self.z % other)

    def align(self, grid_size: int) -> "Vector":
        return self - self % grid_size
