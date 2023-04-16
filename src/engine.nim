import std/[
  algorithm,
  math,
  monotimes,
  sequtils,
  sets,
  strformat,
  tables,
]

import glm
import glm/noise

const
  chunkSize = 16
  terrainHeightMultiplier = 16
  terrainStretch = 32

const (cubeCorners, cubeEdges) = block:
  var
    corners: Table[Vec3[int], seq[Vec3[int]]]
    edges = newSeqOfCap[(Vec3[int], Vec3[int])](12)
  for x in 0..1:
    for y in 0..1:
      for z in 0..1:
        corners[vec3(x, y, z)] = newSeqOfCap[Vec3[int]](3)
  for corner in corners.keys:
    for other in corners.keys:
      for axis in [vec3(1, 0, 0), vec3(0, 1, 0), vec3(0, 0, 1)]:
        if corner + axis == other:
          corners[corner].add(other)
          corners[other].add(corner)
          edges.add((corner, other))
  (corners, edges)

type TerrainSurface* = ref object
  vertices*: seq[Vec3[float32]]

type Chunk* = ref object
  position*: Vec3[int]
  terrainSurfaces*: Table[Vec3[int], seq[TerrainSurface]]

type Array3[W, L, H: static[int]; T] = array[W, array[L, array[H, T]]]

proc newChunk(position: Vec3[int]): Chunk =
  let beginTime = getMonoTime()
  new result
  result.position = position

  let
    zMax = terrainHeightMultiplier
    zMin = -terrainHeightMultiplier
    z0 = position.z
    z1 = z0 + chunkSize

  if z0 > zMax or z1 < zMin:
    echo &"Chunk at {position} is empty"
    return

  let
    x0 = position.x
    y0 = position.y

  var cornerNoise: Array3[chunkSize+1, chunkSize+1, chunkSize+1, float32]
  for x in 0..chunkSize:
    for y in 0..chunkSize:
      for z in 0..chunkSize:
        var v = vec3(float32(x+x0), float32(y+y0), float32(z+z0))
        v /= terrainStretch
        var noise = simplex(v)
        noise *= terrainHeightMultiplier
        noise -= float32(z + z0)
        cornerNoise[x][y][z] = noise

  var cubeEdgeIntersections: Table[(Vec3[int], Vec3[int]), Vec3[float32]]
  var unvisited: HashSet[Vec3[int]]
  var visitNext: seq[Vec3[int]]
  for x in 0..<chunkSize:
    for y in 0..<chunkSize:
      for z in 0..<chunkSize:
        var intersectionCount = 0
        cubeEdgeIntersections.clear
        for edge in cubeEdges:
          let
            (corner0, corner1) = edge
            cnoise0 = cornerNoise[x+corner0.x][y+corner0.y][z+corner0.z]
            cnoise1 = cornerNoise[x+corner1.x][y+corner1.y][z+corner1.z]
            product = cnoise0 * cnoise1

          if product > 0f:
            continue
          elif product == 0f:
            echo(&"Cell at {position + vec3(x, y, z)}",
                 " has corner with 0 noise value, skipping")
            break

          var intersectionPosition: Vec3[float32]
          for i in 0..<3:
            if corner0[i] == corner1[i]:
              intersectionPosition[i] = corner0[i].float32
            else:
              intersectionPosition[i] = cnoise0 / (cnoise0 - cnoise1)
          cubeEdgeIntersections[edge] = intersectionPosition
          intersectionCount += 1

        if intersectionCount == 0:
          continue

        let cell = vec3(x, y, z)
        result.terrainSurfaces[cell] = @[]
        unvisited.clear
        for corner in cubeCorners.keys:
          unvisited.incl(corner)
        while unvisited.len > 0:
          visitNext.add(unvisited.pop)
          var verticesWithNormals: seq[tuple[vertex: Vec3[float32],
                                             normal: Vec3[float32]]]
          while visitNext.len > 0:
            var corner = visitNext.pop
            if cornerNoise[x+corner.x][y+corner.y][z+corner.z] < 0f:
              continue
            for neighbor in cubeCorners[corner]:
              if cornerNoise[x+neighbor.x][y+neighbor.y][z+neighbor.z] < 0f:
                let
                  edge =
                    if (corner.x > neighbor.x or
                        corner.y > neighbor.y or
                        corner.z > neighbor.z):
                      (neighbor, corner)
                    else:
                      (corner, neighbor)
                  vertex = cubeEdgeIntersections[edge]
                  normal = neighbor - corner
                  fnormal = vec3(normal.x.float32,
                                 normal.y.float32,
                                 normal.z.float32)
                verticesWithNormals.add((vertex, fnormal))
              elif neighbor in unvisited:
                visitNext.add(neighbor)
                unvisited.excl(neighbor)

          if verticesWithNormals.len > 0:
            var (vertices, normals) = verticesWithNormals.unzip

            # Point roughly in the center of all the vertices
            let midpoint = vertices.sum / vertices.len.float32
            # Normal vector of the surface's front face
            let mnormal = normals.sum.normalize

            for vertex in vertices.mitems:
              # Vertices relative to the midpoint
              vertex -= midpoint
              # Project the vertex vectors into the plane defined by midpoint
              # and mnormal, and normalize them
              vertex = vertex.cross(mnormal)
              vertex = mnormal.cross(vertex).normalize

            # Angles between first vector and each of the others
            var thetas = newSeq[float32](vertices.len)
            # Angle of first vector with itself is zero
            thetas[0] = 0f
            for i in 1..<len(vertices):
              thetas[i] = vertices[0].dot(vertices[i]).clamp(-1f, 1f).arccos
              # Cross product will point the opposite direction for reflex
              # angles. The dot product of that vector with mnormal will be
              # negative if it's pointing away.
              if vertices[0].cross(vertices[i]).dot(mnormal) < 0f:
                # 2*pi minus angle to get reflex angle
                thetas[i] = 2 * PI - thetas[i]

            # Order surface vertices counter-clockwise around mnormal
            var (orderedVertices, _) = verticesWithNormals.unzip
            var verticesWithThetas = thetas.zip(orderedVertices)
            verticesWithThetas.sort(
              func (a, b: (float32, Vec3[float32])): int = cmp(a[0], b[0])
            )
            (thetas, orderedVertices) = verticesWithThetas.unzip

            var surface = TerrainSurface(vertices: orderedVertices)
            result.terrainSurfaces[cell].add(surface)

  let endTime = getMonoTime()
  echo &"Chunk at {position} initialized in {endTime - beginTime}"

type GameEngine* = ref object
  chunks*: Table[Vec3[int], Chunk]
  playerPosition*: Vec3[int]

proc chunk(gameEngine: GameEngine, x, y, z: int): Chunk =
  let alignedPosition = vec3(x - x.floorMod(chunkSize),
                             y - y.floorMod(chunkSize),
                             z - z.floorMod(chunkSize))
  result = gameEngine.chunks.getOrDefault(alignedPosition)
  if result == nil:
    result = newChunk(alignedPosition)
    gameEngine.chunks[alignedPosition] = result

proc chunk(gameEngine: GameEngine, position: Vec3[int]): Chunk =
  gameEngine.chunk(position.x, position.y, position.z)

proc newGameEngine*(): GameEngine =
  let beginTime = getMonoTime()
  new result
  var (x, y, z) = (0, 0, terrainHeightMultiplier)
  let (xLocal, yLocal) = (x.floorMod(chunkSize), y.floorMod(chunkSize))
  block findPosition:
    while true:
      doAssert z >= -terrainHeightMultiplier
      var chunk = result.chunk(x, y, z)
      if chunk.terrainSurfaces.len == 0:
        z = chunk.position.z - 1
        continue
      for zLocal in countdown(z.floorMod(chunkSize), 0):
        if vec3(xLocal, yLocal, zLocal) in chunk.terrainSurfaces:
          z = chunk.position.z + zLocal + 1
          break findPosition
  result.playerPosition = vec3(x, y, z)

  # Eager load the 125 chunks around the player's position
  for x in -2..2:
    for y in -2..2:
      for z in -2..2:
        discard result.chunk(vec3(x, y, z) * chunkSize + result.playerPosition)

  let endTime = getMonoTime()
  echo &"{result.chunks.len} chunks initialized in {endTime - beginTime}"
