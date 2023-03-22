import collections
import itertools
import time

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
        self.terrain_surfaces = collections.defaultdict(list)
        self.make_cube_graph()
        cube_graph = self.cube_graph

        z_max = defs.TERRAIN_HEIGHT_MULTIPLIER
        z_min = -defs.TERRAIN_HEIGHT_MULTIPLIER
        z0 = position.z
        z1 = z0 + defs.CHUNK_SIZE

        if z0 > z_max or z1 < z_min:
            print(f"Chunk at {self.position} is empty")
            return

        begin_time = time.time()

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

        for local in np.argwhere(intersections > 0):
            skip_cell = False

            for node in cube_graph.nodes:
                corner_noise = noise[node+local]

                if corner_noise == 0:
                    print(f"Cell at {position + local} has corner with 0 "
                          "noise value, skipping")
                    skip_cell = True
                    break

                cube_graph.node_data[node] = corner_noise

            if skip_cell:
                continue

            for edge in cube_graph.edges:
                corner0, corner1 = edge
                cnoise0 = cube_graph.node_data[corner0]
                cnoise1 = cube_graph.node_data[corner1]

                if cnoise0 * cnoise1 > 0:
                    cube_graph.edges[edge] = None
                else:
                    intersection = cnoise0 / (cnoise0 - cnoise1)
                    vertex = (corner1 - corner0) * intersection + corner0
                    cube_graph.edges[edge] = vertex

            unvisited = set(cube_graph.nodes.keys())
            surface_vertices = list()

            while unvisited:
                visit_next = list()
                visit_next.append(unvisited.pop())

                while visit_next:
                    node = visit_next.pop()

                    if cube_graph.node_data[node] < 0:
                        continue

                    for neighbor in cube_graph.nodes[node]:
                        if cube_graph.node_data[neighbor] < 0:
                            edge = cube_graph.edge_key(node, neighbor)
                            vertex = cube_graph.edges[edge]
                            normal = neighbor - node
                            surface_vertices.append((vertex, normal))
                        elif neighbor in unvisited:
                            visit_next.append(neighbor)
                            unvisited.remove(neighbor)

                if surface_vertices:
                    vertices, normals = zip(*surface_vertices)
                    vertices = np.array(vertices, dtype=np.float64)
                    normals = np.array(normals, dtype=np.float64)

                    # Point roughly in the center of all the vertices
                    midpoint = vertices.mean(axis=0)
                    # Vertices relative to the midpoint
                    vertices -= midpoint

                    # Normal vector of the surface's front face
                    mnormal = normals.mean(axis=0)
                    # Normalize
                    mnormal /= np.linalg.norm(mnormal)

                    # Project the vertex vectors into the plane defined by
                    # midpoint and mnormal, and normalize them
                    vproject = np.cross(vertices, mnormal)
                    vproject = np.cross(mnormal, vproject)
                    vproject /= np.linalg.norm(vproject, axis=1)[:, None]

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
                    _, ordered_vertices = zip(*order)

                    loc = Vector(*local)
                    self.terrain_surfaces[loc].append(ordered_vertices)
                    surface_vertices.clear()

        end_time = time.time()
        time_diff = end_time - begin_time
        print(f"Chunk at {self.position} initialized in {time_diff}s")

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
