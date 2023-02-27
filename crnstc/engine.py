import itertools
import math
import statistics
import time

import numpy as np
import opensimplex

from crnstc import definitions as defs
from crnstc.geometry import Vector


class GameEngine:
    def __init__(self):
        opensimplex.seed(0)
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
    cells_from_noise = np.frompyfunc(lambda n: 0 if n < 0 else 1,
                                     1, 1)

    def __init__(self, position: Vector):
        self.position = position

        if position.z > defs.TERRAIN_HEIGHT_MULTIPLIER:
            self.cells = np.zeros(defs.CHUNK_SHAPE, dtype=np.uint8)
            print(f"Chunk at {self.position} is empty")
            return

        begin_time = time.time()

        x_indices = np.linspace(
            position.x / defs.TERRAIN_STRETCH,
            (position.x + defs.CHUNK_SIZE - 1) / defs.TERRAIN_STRETCH,
            num=defs.CHUNK_SIZE,
            dtype=np.float64,
        )
        y_indices = np.linspace(
            position.y / defs.TERRAIN_STRETCH,
            (position.y + defs.CHUNK_SIZE - 1) / defs.TERRAIN_STRETCH,
            num=defs.CHUNK_SIZE,
            dtype=np.float64,
        )
        z_indices = np.linspace(
            position.z / defs.TERRAIN_STRETCH,
            (position.z + defs.CHUNK_SIZE - 1) / defs.TERRAIN_STRETCH,
            num=defs.CHUNK_SIZE,
            dtype=np.float64,
        )
        noise = opensimplex.noise3array(x_indices, y_indices, z_indices)
        noise *= defs.TERRAIN_HEIGHT_MULTIPLIER
        noise -= position.z
        noise -= np.arange(defs.CHUNK_SIZE)
        self.cells = self.cells_from_noise(noise)
        self.cells = self.cells.astype(np.int8)

        end_time = time.time()
        time_diff = end_time - begin_time
        print(f"Chunk at {self.position} initialized in {time_diff}s")
