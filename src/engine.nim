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
    # Each permutation is a set of 8 bits, one bit per corner of the cube. 1s
    # are corners with positive noise values, 0s are corners with negative
    # noise values.
    var directedEdges: seq[byte]
    for corner in 0b000'u8..0b111'u8:
      # The index of each corner (0 through 7) is treated as a vector of 3
      # bits, arranged 0b_xyz, giving the position of the corner
      for flip in [0b001'u8, 0b010'u8, 0b100'u8]:
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

proc aligned(position: Vec3l, gridSize: int): Vec3l =
  position - position.floorMod(gridSize)

type OctreeNode*[T] = ref object
  position*: Vec3l
  size*: range[1..chunkSize]
  parent*: OctreeNode[T]
  children*: array[0b000'u8..0b111'u8, OctreeNode[T]]
  data*: seq[T]

proc newOctreeNode[T](position: Vec3l, size: int,
                      parent: OctreeNode[T]): OctreeNode[T] =
  new result
  result.position = position.aligned(size)
  result.size = size
  result.parent = parent

proc newOctreeRoot[T](position: Vec3l): OctreeNode[T] =
  newOctreeNode[T](position, chunkSize, nil)

proc canContain[T](tree: OctreeNode[T], position: Vec3l): bool =
  (position.greaterThanEqual(tree.position).all and
   position.lessThan(tree.position + tree.size).all)

proc insert[T](tree: OctreeNode[T], position: Vec3l, item: T) =
  if not tree.canContain(position):
    assert tree.size != tree.size.typeof.high
    tree.parent.insert(position, item)
  elif tree.size > tree.size.typeof.low:
    let
      halfSize = tree.size shr 1
      internalPosition = position - tree.position
    var childIndex: byte
    for i, value in internalPosition.arr:
      if value >= halfSize:
        childIndex.setBit(2-i)
    if tree.children[childIndex] == nil:
      tree.children[childIndex] = newOctreeNode[T](position, halfSize, tree)
    tree.children[childIndex].insert(position, item)
  else:
    tree.data.add(item)

iterator items*[T](tree: OctreeNode[T]): T =
  var
    nodeQueue = @[tree]
    i = 0
  while i < nodeQueue.len:
    let node = nodeQueue[i]
    for item in node.data:
      yield item
    for child in node.children:
      if child != nil:
        nodeQueue.add(child)
    i.inc

type TerrainSurface* = ref object
  position*: Vec3l
  vertices*: seq[Vec3[float32]]
  normal*: Vec3[float32]
  walkHeight*: Option[float32]

proc insert(tree: OctreeNode[TerrainSurface], surface: TerrainSurface) =
  tree.insert(surface.position, surface)

type Array3[W, L, H: static[int]; T] = array[W, array[L, array[H, T]]]

proc newChunk(position: Vec3l): OctreeNode[TerrainSurface] =
  let beginTime = getMonoTime()
  result = newOctreeRoot[TerrainSurface](position)

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
        var v = toFloat32(position + vec3l(x, y, z))
        v /= terrainStretch
        var noise = simplex(v)
        noise *= terrainHeightMultiplier
        noise -= float32(z + z0)
        cornerNoise[x][y][z] = noise

  for x in 0..<chunkSize:
    for y in 0..<chunkSize:
      for z in 0..<chunkSize:
        var permutation: byte
        for bit in 0b000'u8..0b111'u8:
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
          cell = vec3l(x, y, z)

        for connectedEdgeSet in edgeConnections:
          var surface = TerrainSurface()
          surface.position = position + cell
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

          result.insert(surface)

  let endTime = getMonoTime()
  echo &"Chunk at {position} initialized in {endTime - beginTime}"

type GameEngine* = ref object
  chunks*: Table[Vec3l, OctreeNode[TerrainSurface]]
  playerPosition*: Vec3l

proc chunk(self: GameEngine, position: Vec3l): OctreeNode[TerrainSurface] =
  let alignedPosition = position.aligned(chunkSize)
  result = self.chunks.getOrDefault(alignedPosition)
  if result == nil:
    result = newChunk(alignedPosition)
    self.chunks[alignedPosition] = result

proc chunk(self: GameEngine, x, y, z: int): OctreeNode[TerrainSurface] =
  self.chunk(vec3l(x, y, z))

proc walkableSurfaces(self: OctreeNode,
                      lowerCorner, upperCorner: Vec3l): seq[TerrainSurface] =
  let
    upperMax = self.position + self.size
    lc = lowerCorner.clamp(self.position, upperMax)
    uc = upperCorner.clamp(self.position, upperMax)
  if lc.greaterThanEqual(uc).any:
    return
  elif self.size == self.size.typeof.low:
    # Normally we'd check branch nodes for matches too, but TerrainSurfaces
    # can't currently span cells
    for surface in self.data:
     if surface.walkHeight.isSome:
       result.add(surface)
  else:
    for child in self.children:
      if child != nil:
        result.add(child.walkableSurfaces(lc, uc))

proc walkableSurface(self: GameEngine,
                     lowerCorner, upperCorner: Vec3l): TerrainSurface =
  ## Find the highest walkable surface in the given bounding box
  assert lowerCorner.lessThan(upperCorner).all
  var lc = lowerCorner
  lc.z = lc.z.max(-terrainHeightMultiplier)
  var uc = upperCorner
  uc.z = uc.z.min(terrainHeightMultiplier + 1)
  let
    lowerChunk = lc.aligned(chunkSize)
    upperChunk = aligned(uc - 1, chunkSize)
  for z in countdown(upperChunk.z, lowerChunk.z, chunkSize):
    for x in countup(lowerChunk.x, upperChunk.x, chunkSize):
      for y in countup(lowerChunk.y, upperChunk.y, chunkSize):
        var surfaces = self.chunk(x, y, z).walkableSurfaces(lc, uc)
        if surfaces.len == 0:
          continue
        surfaces.sort(
          func(a, b: TerrainSurface): int = a.position.z.cmp(b.position.z)
        )
        return surfaces[^1]

proc playerSurface*(self: GameEngine): TerrainSurface =
  self.walkableSurface(self.playerPosition, self.playerPosition + 1)

proc newGameEngine*(): GameEngine =
  let beginTime = getMonoTime()
  new result
  let spawnSurface = result.walkableSurface(
    vec3l(0, 0, -terrainHeightMultiplier),
    vec3l(1, 1, terrainHeightMultiplier),
  )
  doAssert spawnSurface != nil
  result.playerPosition = spawnSurface.position

  # Eager load the 125 chunks around the player's position
  for x in -2..2:
    for y in -2..2:
      for z in -2..2:
        discard result.chunk(vec3l(x, y, z) * chunkSize + result.playerPosition)

  let endTime = getMonoTime()
  echo &"{result.chunks.len} chunks initialized in {endTime - beginTime}"

proc attemptMove*(self: GameEngine, direction: Vec3l): bool =
  var lowerCorner = self.playerPosition + direction
  var upperCorner = lowerCorner + 1
  lowerCorner.z -= 1
  upperCorner.z += 1
  let destination = self.walkableSurface(lowerCorner, upperCorner)
  if destination != nil:
    self.playerPosition = destination.position
    return true
