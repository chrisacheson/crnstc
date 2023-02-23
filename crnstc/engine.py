import itertools
import math
import statistics
import time

import numpy as np

from crnstc import definitions as defs
from crnstc.geometry import Vector


class GameEngine:
    def __init__(self):
        self.chunks = dict()

        player_z = defs.TERRAIN_HEIGHT_MULTIPLIER + 1

        begin_time = time.time()

        while self.get_cell(Vector(0, 0, player_z-1)) == 0:
            player_z -= 1

        self.player_position = Vector(0, 0, player_z)

        for x, y, z in itertools.product(range(-32, 33, 16), repeat=3):
            self.get_cell(Vector(x, y, z) + self.player_position)

        end_time = time.time()
        time_diff = end_time - begin_time
        print(f"{len(self.chunks)} chunks initialized in {time_diff}s")

    def get_chunk(self, position: Vector) -> "Chunk":
        aligned = position.align(defs.CHUNK_SIZE)

        if aligned not in self.chunks:
            chunk = Chunk(aligned)
            self.chunks[aligned] = chunk
        else:
            chunk = self.chunks[aligned]

        return chunk

    def get_cell(self, position: Vector) -> int:
        chunk = self.get_chunk(position)
        local = position % defs.CHUNK_SIZE

        return chunk.cells[local]


class Chunk:
    def __init__(self, position: Vector):
        begin_time = time.time()
        self.position = position
        self.cells = np.empty(defs.CHUNK_SHAPE, dtype=np.uint8)

        for local in np.ndindex(self.cells.shape):
            x, y, z = local
            xoff, yoff, zoff = self.position
            z += zoff

            if z > defs.TERRAIN_HEIGHT_MULTIPLIER:
                self.cells[local] = 0
                continue

            x += xoff
            y += yoff

            x_sine = math.sin(x / defs.TERRAIN_STRETCH)
            y_sine = math.sin(y / defs.TERRAIN_STRETCH)
            z_sine = math.sin(z / defs.TERRAIN_STRETCH)

            height = (defs.TERRAIN_HEIGHT_MULTIPLIER
                      * statistics.fmean((x_sine, y_sine, z_sine)))

            self.cells[local] = 0 if z > height else 1

        end_time = time.time()
        time_diff = end_time - begin_time
        print(f"Chunk at {self.position} initialized in {time_diff}s")
