import itertools
import math
import time

import numba
import numpy as np
import opensimplex

from crnstc import definitions as defs
from crnstc.geometry import Vector
from crnstc.graph import Graph


class GameEngine:
    def __init__(self):
        opensimplex.seed(0)
        self.chunks = dict()

        begin_time = time.time()

        x, y, z = 0, 0, defs.TERRAIN_HEIGHT_MULTIPLIER

        do = True
        while do:
            chunk = self.get_chunk(Vector(x, y, z))

            if len(chunk.terrain_surfaces) == 0:
                z = chunk.position.z - 1
                continue

            for i in range(z % defs.CHUNK_SIZE, -1, -1):
                if Vector(x, y, i) % defs.CHUNK_SIZE in chunk.terrain_surfaces:
                    z = chunk.position.z + i + 1
                    do = False
                    break

        self.player_position = Vector(x, y, z)

        for x, y, z in itertools.product(range(-32, 33, 16), repeat=3):
            self.get_chunk(Vector(x, y, z) + self.player_position)

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


class Chunk:
    cube_graph = None

    def __init__(self, position: Vector):
        self.position = position
        self.make_cube_graph()
        cube_graph = self.cube_graph

        z_max = defs.TERRAIN_HEIGHT_MULTIPLIER
        z_min = -defs.TERRAIN_HEIGHT_MULTIPLIER
        z0 = position.z
        z1 = z0 + defs.CHUNK_SIZE

        if z0 > z_max or z1 < z_min:
            print(f"Chunk at {self.position} is empty")
            self.terrain_surfaces = dict()
            return

        begin_time = time.perf_counter()

        x0 = position.x
        x1 = x0 + defs.CHUNK_SIZE
        y0 = position.y
        y1 = y0 + defs.CHUNK_SIZE

        x_corners = np.linspace(x0 / defs.TERRAIN_STRETCH,
                                x1 / defs.TERRAIN_STRETCH,
                                num=defs.CHUNK_SIZE + 1, dtype=np.float64)
        y_corners = np.linspace(y0 / defs.TERRAIN_STRETCH,
                                y1 / defs.TERRAIN_STRETCH,
                                num=defs.CHUNK_SIZE + 1, dtype=np.float64)
        z_corners = np.linspace(z0 / defs.TERRAIN_STRETCH,
                                z1 / defs.TERRAIN_STRETCH,
                                num=defs.CHUNK_SIZE + 1, dtype=np.float64)

        # OpenSimplex gives values as z,y,x, so swap x and z coordinates
        noise = opensimplex.noise3array(z_corners, y_corners, x_corners)
        noise *= defs.TERRAIN_HEIGHT_MULTIPLIER
        noise -= np.arange(z0, z1 + 1, dtype=np.float64)

        products = np.empty(defs.CHUNK_SHAPE, dtype=np.float64)
        intersections = np.zeros(defs.CHUNK_SHAPE, dtype=np.uint8)

        for edge in cube_graph.edges:
            corner0, corner1 = edge
            slice0 = (slice(corner0.x, defs.CHUNK_SIZE + corner0.x),
                      slice(corner0.y, defs.CHUNK_SIZE + corner0.y),
                      slice(corner0.z, defs.CHUNK_SIZE + corner0.z))
            slice1 = (slice(corner1.x, defs.CHUNK_SIZE + corner1.x),
                      slice(corner1.y, defs.CHUNK_SIZE + corner1.y),
                      slice(corner1.z, defs.CHUNK_SIZE + corner1.z))
            np.multiply(noise[slice0], noise[slice1], out=products)
            intersections[products < 0] += 1

        terrain_cells = np.argwhere(intersections > 0)

        find_intersections_time = time.perf_counter()

        terrain_surfaces = numba_make_terrain_surfaces(
            noise,
            terrain_cells,
            self.numba_cube_nodes,
            self.numba_cube_edges,
        )
        self.terrain_surfaces = {Vector(*cell): csurfaces
                                 for cell, csurfaces
                                 in zip(terrain_cells, terrain_surfaces)}

        end_time = time.perf_counter()
        diff0 = find_intersections_time - begin_time
        diff0 = round(diff0, 4)
        diff1 = end_time - find_intersections_time
        diff1 = round(diff1, 4)
        diff_full = end_time - begin_time
        diff_full = round(diff_full, 4)
        print(f"Chunk at {self.position} initialized in {diff_full}s "
              f"({diff0}s + {diff1}s)")

    def make_cube_graph(self):
        if self.cube_graph is not None:
            return

        cube_graph = Graph()
        swd = Vector(0, 0, 0)
        sed = Vector(1, 0, 0)
        nwd = Vector(0, 1, 0)
        ned = Vector(1, 1, 0)
        swu = Vector(0, 0, 1)
        seu = Vector(1, 0, 1)
        nwu = Vector(0, 1, 1)
        neu = Vector(1, 1, 1)

        # x edges
        cube_graph.add_edge(swd, sed)
        cube_graph.add_edge(nwd, ned)
        cube_graph.add_edge(swu, seu)
        cube_graph.add_edge(nwu, neu)

        # y edges
        cube_graph.add_edge(swd, nwd)
        cube_graph.add_edge(sed, ned)
        cube_graph.add_edge(swu, nwu)
        cube_graph.add_edge(seu, neu)

        # z edges
        cube_graph.add_edge(swd, swu)
        cube_graph.add_edge(sed, seu)
        cube_graph.add_edge(nwd, nwu)
        cube_graph.add_edge(ned, neu)

        self.__class__.cube_graph = cube_graph

        numba_cube_nodes = numba.typed.Dict()
        numba_cube_edges = numba.typed.Dict()

        for node, neighbors in cube_graph.nodes.items():
            # Numba doesn't have typed sets yet. Tuple is fine here.
            numba_cube_nodes[node] = tuple(neighbors)

        for edge in cube_graph.edges:
            # Numba dicts can't have optional/None values. Use this dict as a
            # fake set by setting its values to zero. Track edge values in a
            # separate dict.
            numba_cube_edges[edge] = 0

        self.__class__.numba_cube_nodes = numba_cube_nodes
        self.__class__.numba_cube_edges = numba_cube_edges


@numba.njit(cache=True)
def numba_make_terrain_surfaces(noise, cells, cube_nodes, cube_edges):
    terrain_surfaces = list()
    edge_values = dict()

    for local in cells:
        x0, y0, z0 = local
        cell_noise = noise[x0:x0+2, y0:y0+2, z0:z0+2]

        if (cell_noise == 0).any():
            print(f"Cell at local position {x0}, {y0}, {z0} "
                  "has corner with 0 noise value, skipping")
            continue

        for edge in cube_edges:
            corner0, corner1 = edge
            cnoise0 = cell_noise[(corner0.x, corner0.y, corner0.z)]
            cnoise1 = cell_noise[(corner1.x, corner1.y, corner1.z)]

            if cnoise0 * cnoise1 < 0:
                intersection = cnoise0 / (cnoise0 - cnoise1)
                vertex = vec_add(
                    vec_mul(vec_sub(corner1, corner0), intersection),
                    corner0,
                )
                edge_values[edge] = vertex

        unvisited = set(cube_nodes.keys())
        cell_surfaces = list()
        surface_vertices = list()

        while unvisited:
            visit_next = list()
            visit_next.append(unvisited.pop())

            while visit_next:
                node = visit_next.pop()

                if cell_noise[(node.x, node.y, node.z)] < 0:
                    continue

                for neighbor in cube_nodes[node]:
                    if cell_noise[(neighbor.x, neighbor.y, neighbor.z)] < 0:
                        edge = ((node, neighbor) if node < neighbor
                                else (neighbor, node))
                        vertex = edge_values[edge]
                        normal = vec_sub(neighbor, node)
                        surface_vertices.append((vertex, normal))
                    elif neighbor in unvisited:
                        visit_next.append(neighbor)
                        unvisited.remove(neighbor)

            if surface_vertices:
                num_vertices = len(surface_vertices)
                vertices = np.empty((num_vertices, 3), dtype=np.float64)
                normals = np.empty((num_vertices, 3), dtype=np.float64)

                # Was: vertices, normals = zip(*surface_vertices)
                for i in range(num_vertices):
                    vertex, normal = surface_vertices[i]

                    for j in range(3):
                        vertices[i, j] = vertex[j]
                        normals[i, j] = normal[j]

                # Point roughly in the center of all the vertices
                midpoint = np_mean_axis0(vertices)
                # Vertices relative to the midpoint
                vertices -= midpoint

                # Normal vector of the surface's front face
                mnormal = np_mean_axis0(normals)
                # Normalize
                mnormal /= np_magnitude(mnormal)

                # Project the vertex vectors into the plane defined by
                # midpoint and mnormal, and normalize them
                vproject = np.cross(vertices, mnormal)
                vproject = np.cross(mnormal, vproject)
                # Numba 0.56.4 doesn't support numpy.newaxis/None
                vproject /= np.expand_dims(
                    np.sqrt((vproject ** 2).sum(axis=1)),
                    axis=1,
                )

                # First vector
                head = vproject[0, :]
                # Remaining vectors
                tail = vproject[1:, :]

                # Angles between first vector and each of the others
                thetas = np.arccos(np.sum(tail * head, axis=1))

                # Cross product will point the opposite direction for
                # reflex angles
                tcross = np.cross(head, tail)
                # Dot product will be negative for vectors pointing away
                # from mnormal
                tndot = np.sum(tcross * mnormal, axis=1)
                # Indices of angles to be flipped
                reflex = tndot < 0

                # 2*pi - angle to get reflex angle
                thetas[reflex] *= -1
                thetas[reflex] += 2 * np.pi

                # Prepend a 0 degree angle for the first vector with itself
                thetas = list(thetas)
                thetas.insert(0, 0)

                # Order surface vertices counter-clockwise around mnormal
                order = sorted(zip(thetas, surface_vertices))
                # Was: _, ordered_vertices = zip(*order)
                ordered_vertices = [v_n for theta, v_n in order]

                cell_surfaces.append(ordered_vertices)
                surface_vertices.clear()

        if cell_surfaces:
            terrain_surfaces.append(cell_surfaces)

        edge_values.clear()

    return terrain_surfaces


@numba.njit(cache=True)
def vec_add(a, b):
    return Vector(x=a[0] + b[0],
                  y=a[1] + b[1],
                  z=a[2] + b[2])


@numba.njit(cache=True)
def vec_sub(a, b):
    return Vector(x=a[0] - b[0],
                  y=a[1] - b[1],
                  z=a[2] - b[2])


@numba.njit(cache=True)
def vec_mul(vec, multiplier):
    return Vector(x=vec[0] * multiplier,
                  y=vec[1] * multiplier,
                  z=vec[2] * multiplier)


@numba.njit(cache=True)
def np_mean_axis0(arr):
    # Numba doesn't support axis argument for mean
    result = np.empty(arr.shape[1], dtype=np.float64)

    for i in range(len(result)):
        result[i] = arr[:, i].mean()

    return result


@numba.njit(cache=True)
def np_magnitude(arr):
    # Numba requires scipy for numpy.linalg.norm
    return math.sqrt((arr ** 2).sum())
