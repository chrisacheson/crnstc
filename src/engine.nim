import std/[
  algorithm,
  bitops,
  math,
  monotimes,
  options,
  strformat,
  tables,
]

import glm
import glm/noise

import glm_helper

const
  chunkSize = 16
  terrainHeightMultiplier = 16
  terrainStretch = 32
  upVector = vec3(0f, 0f, 1f)
  cellMidpoint = vec3(0.5f, 0.5f, 0.5f)
  maxWalkableIncline = PI / 4

type Word = range[0b0000'u8..0b1111'u8]

proc packWords(high, low: Word): byte =
  result = (high shl 4) or low

proc unpackWords(b: byte): tuple[high, low: Word] =
  result.high = b shr 4
  result.low = b and 0b0000_1111'u8

# All 256 possible combinations of positive/negative cube corners, with their
# respective sets of edge intersection connections
const marchingCubesPermutations = block:
  var permutations: array[low(byte)..high(byte), seq[seq[byte]]]
  for permutation in low(byte)..high(byte):
    # Each permutation is a sef of 8 bits, one bit per corner of the cube. 1s
    # are corners with positive noise values, 0s are corners with negative
    # noise values.
    var directedEdges: seq[byte]
    for corner in 0b000'u8..0b111:
      # The index of each corner (0 through 7) is treated as a vector of 3
      # bits, arranged 0b_xyz, giving the position of the corner
      for flip in [0b001'u8, 0b010, 0b100]:
        # Neighbors of a corner can be found by doing a single flip on each
        # of the corner's 3 bits
        let neighbor = corner xor flip
        if permutation.testBit(corner) and not permutation.testBit(neighbor):
          # Edges are stored as single bytes, arranged 0b0xyz_0xyz. The high
          # word is set to the position of the positive corner and the low word
          # is set to the position of the negative corner.
          directedEdges.add(packWords(corner, neighbor))

    directedEdges.sort
    while directedEdges.len > 0:
      assert directedEdges.len >= 3
      # Arrange the edges into sets connected edges, one for each surface that
      # will be created
      var connectedEdges = @[directedEdges[0]]
      directedEdges.delete(0)
      var doLoop = true
      while doLoop:
        # With the edge vector (from positive corner to negative corner)
        # pointing up, find the corners of its righthand face
        #
        # +---------+. 
        # |`.   ^     `.
        # |  `. |       `.
        # |    `|---------+
        # |left |         |
        # |face |  right  |
        # +     |  face   |
        #  `.   |         |
        #    `. |         |
        #      `|---------+
        #       |
        #     vector
        #
        let (lowerLeftCorner, upperLeftCorner) = connectedEdges[^1].unpackWords

        var axis = countTrailingZeroBits(lowerLeftCorner xor upperLeftCorner)
        if lowerLeftCorner.parityBits == 0:
          # Rotate right
          axis -= 1
        else:
          # Rotate left
          axis += 1
        axis = axis.floorMod(3)

        var lowerRightCorner = lowerLeftCorner
        lowerRightCorner.flipBit(axis)
        var upperRightCorner = upperLeftCorner
        upperRightCorner.flipBit(axis)

        # Bit set of corners included in this face
        var faceCorners = byte.low
        faceCorners.setBits(lowerLeftCorner.byte, upperLeftCorner.byte,
                            lowerRightCorner.byte, upperRightCorner.byte)

        for i, candidate in directedEdges:
          # Check each remaining edge to find a valid connection
          let (posCorner, negCorner) = candidate.unpackWords
          if (
            # n<--p
            # ^
            # |
            # p   ?
            (posCorner == upperRightCorner and negCorner == upperLeftCorner) or
            # n   n
            # ^   ^
            # |   |
            # p   p
            (posCorner == lowerRightCorner and negCorner == upperRightCorner) or
            # n   n
            # ^
            # |
            # p-->n
            (posCorner == lowerLeftCorner and negCorner == lowerRightCorner and
             not permutation.testBit(upperRightCorner.byte))
          ):
            connectedEdges.add(candidate)
            directedEdges.delete(i)
            if directedEdges.len == 0:
              # No ungrouped edges remaining
              doLoop = false
            break

          elif i == directedEdges.high:
            # None of the remaining ungrouped edges are valid for this set,
            # start a new set
            doLoop = false

      assert connectedEdges.len >= 3
      permutations[permutation].add(connectedEdges)

  permutations

type TerrainSurface* = ref object
  vertices*: seq[Vec3[float32]]
  normal*: Vec3[float32]
  walkHeight*: Option[float32]

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

  var cornerNoise: Array3[chunkSize+1, chunkSize+1, chunkSize+1, float32]
  for x in 0..chunkSize:
    for y in 0..chunkSize:
      for z in 0..chunkSize:
        var v = toFloat32(position + vec3(x, y, z))
        v /= terrainStretch
        var noise = simplex(v)
        noise *= terrainHeightMultiplier
        noise -= float32(z + z0)
        cornerNoise[x][y][z] = noise

  for x in 0..<chunkSize:
    for y in 0..<chunkSize:
      for z in 0..<chunkSize:
        var permutation: byte
        for bit in 0b000'u8..0b111:
          # Check noise values at each corner of the current cell to determine
          # which marching cubes permutation applies
          let
            nx = x + bit.testBit(2).int
            ny = y + bit.testBit(1).int
            nz = z + bit.testBit(0).int
            noise = cornerNoise[nx][ny][nz]
          if noise >= 0f:
            permutation.setBit(bit)

        let
          edgeConnections = marchingCubesPermutations[permutation]
          cell = vec3(x, y, z)
        if edgeConnections.len > 0:
          result.terrainSurfaces[cell] = @[]

        for connectedEdgeSet in edgeConnections:
          var surface = TerrainSurface()
          for edge in connectedEdgeSet:
            let
              (posCorner, negCorner) = edge.unpackWords
              pcx = posCorner.testBit(2).int
              pcy = posCorner.testBit(1).int
              pcz = posCorner.testBit(0).int
              pcNoise = cornerNoise[x+pcx][y+pcy][z+pcz]
              pcPosition = vec3(pcx, pcy, pcz)
              ncx = negCorner.testBit(2).int
              ncy = negCorner.testBit(1).int
              ncz = negCorner.testBit(0).int
              ncNoise = cornerNoise[x+ncx][y+ncy][z+ncz]
              ncPosition = vec3(ncx, ncy, ncz)
            # Interpolate between corner noise values to determine the point
            # where the terrain surface should intersect the edge
            var vertex = toFloat32(ncPosition - pcPosition)
            vertex *= pcNoise / (pcNoise - ncNoise)
            vertex += pcPosition
            surface.vertices.add(vertex)

          let midpoint = surface.vertices.sum / surface.vertices.len.float32
          var
            sumNormals: Vec3f
            numNormals = surface.vertices.len
          if numNormals == 3:
            # For a triangle, the vertices are guaranteed to be coplanar, so we
            # don't need to take an average
            numNormals = 1

          for i in 0..<numNormals:
            # Terrain surfaces with more than 3 vertices aren't actually flat,
            # so calculate normals for each pair of adjacent vertices with the
            # midpoint, and average them
            let
              vertexA = surface.vertices[i]
              vertexB = surface.vertices[floorMod(i+1, surface.vertices.len)]
              vectorMA = vertexA - midpoint
              vectorMB = vertexB - midpoint
            sumNormals += vectorMA.cross(vectorMB)

          surface.normal = sumNormals.normalize

          # Determine if the surface can be walked on, and its elevation within
          # the cell
          #
          # https://en.wikipedia.org/wiki/Line%E2%80%93plane_intersection
          let
            normDotUp = surface.normal.dot(upVector).clamp(-1f, 1f)
            incline = normDotUp.arccos
          if incline <= maxWalkableIncline:
            let
              d = surface.normal.dot(midpoint - cellMidpoint) / normDotUp
              intersection = cellMidpoint + d * upVector
            if intersection.z >= 0f and intersection.z <= 1f:
              surface.walkHeight = some(intersection.z)

          result.terrainSurfaces[cell].add(surface)

  let endTime = getMonoTime()
  echo &"Chunk at {position} initialized in {endTime - beginTime}"

type GameEngine* = ref object
  chunks*: Table[Vec3[int], Chunk]
  playerPosition*: Vec3[int]

proc chunk(self: GameEngine, position: Vec3[int]): Chunk =
  let alignedPosition = position - position.floorMod(chunkSize)
  result = self.chunks.getOrDefault(alignedPosition)
  if result == nil:
    result = newChunk(alignedPosition)
    self.chunks[alignedPosition] = result

proc chunk(self: GameEngine, x, y, z: int): Chunk =
  self.chunk(vec3(x, y, z))

proc cell(self: GameEngine, position: Vec3[int]): seq[TerrainSurface] =
  self.chunk(position).terrainSurfaces
    .getOrDefault(position.floorMod(chunkSize), @[])

proc playerSurface*(self: GameEngine): TerrainSurface =
  let surfaces = self.cell(self.playerPosition)
  for surface in surfaces:
    if surface.walkHeight.isSome:
      return surface

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
        let cell = vec3(xLocal, yLocal, zLocal)
        if cell in chunk.terrainSurfaces:
          let surfaces = chunk.terrainSurfaces[cell]
          doAssert surfaces.len == 1
          doAssert surfaces[0].walkHeight.isSome
          z = chunk.position.z + zLocal
          break findPosition
  result.playerPosition = vec3(x, y, z)

  # Eager load the 125 chunks around the player's position
  for x in -2..2:
    for y in -2..2:
      for z in -2..2:
        discard result.chunk(vec3(x, y, z) * chunkSize + result.playerPosition)

  let endTime = getMonoTime()
  echo &"{result.chunks.len} chunks initialized in {endTime - beginTime}"

proc attemptMove*(self: GameEngine, direction: Vec3[int]): bool =
  for z in -1..1:
    var candidateCell = self.playerPosition + direction
    candidateCell.z += z
    var candidateSurfaces = self.cell(candidateCell)
    for candidateSurface in candidateSurfaces:
      if candidateSurface.walkHeight.isSome:
        self.playerPosition = candidateCell
        return true
