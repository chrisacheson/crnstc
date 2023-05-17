import std/[
  math,
  monotimes,
  options,
  strformat,
  sugar,
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

const
  axes = [vec3(1, 0, 0), vec3(0, 1, 0), vec3(0, 0, 1)]
  axisPairs = collect: # xy, yz, zx
    for i in 0..<len(axes): (axes[i], axes[(i+1) mod axes.len])
  (cubeCorners, cubeEdges) = block:
    var
      corners: Table[Vec3[int], seq[Vec3[int]]]
      edges = newSeqOfCap[(Vec3[int], Vec3[int])](12)
    for x in 0..1:
      for y in 0..1:
        for z in 0..1:
          corners[vec3(x, y, z)] = newSeqOfCap[Vec3[int]](3)
    for corner in corners.keys:
      for other in corners.keys:
        for axis in axes:
          if corner + axis == other:
            corners[corner].add(other)
            corners[other].add(corner)
            edges.add((corner, other))
    (corners, edges)

type TerrainSurface* = ref object
  vertices*: array[4, Vec3[float32]]
  normal*: Vec3[float32]
  walkPosition*: Option[Vec3[float32]]

type Chunk* = ref object
  position*: Vec3[int]
  terrainSurfaces*: seq[TerrainSurface]

type
  Array3[W, L, H: static[int]; T] = array[W, array[L, array[H, T]]]
  ChunkNoise = array[-1..chunkSize,
                     array[-1..chunkSize,
                           array[-1..chunkSize, float32]]]
  VertexWithNormal = tuple
    vertex: Vec3[float32]
    normal: Vec3[float32]

proc makeNoise(position: Vec3[int]): ChunkNoise =
  for x in -1..chunkSize:
    for y in -1..chunkSize:
      for z in -1..chunkSize:
        var noiseInput = toFloat32(position + vec3(x, y, z))
        noiseInput /= terrainStretch
        var noise = simplex(noiseInput)
        noise *= terrainHeightMultiplier
        noise -= float32(z + position.z)
        result[x][y][z] = noise

proc findVertex(noise: ChunkNoise,
                localPosition: Vec3[int]): Option[VertexWithNormal] =
  var hasPositive, hasNegative = false
  for corner in cubeCorners.keys:
    let cPos = localPosition + corner - 1
    let cornerNoise = noise[cPos.x][cPos.y][cPos.z]
    if cornerNoise > 0:
      hasPositive = true
    elif cornerNoise < 0:
      hasNegative = true

    if hasPositive and hasNegative:
      break

  if not (hasPositive and hasNegative):
    return

  var normal = vec3(0f, 0f, 0f)
  var intersectionPositions: seq[Vec3[float32]]
  for (corner0, corner1) in cubeEdges:
    let
      axis = corner1 - corner0
      cPos0 = localPosition + corner0 - 1
      cPos1 = localPosition + corner1 - 1
      cNoise0 = noise[cPos0.x][cPos0.y][cPos0.z]
      cNoise1 = noise[cPos1.x][cPos1.y][cPos1.z]
      product = cNoise0 * cNoise1
    normal -= (cNoise1 - cNoise0) * axis

    if product > 0f:
      continue

    intersectionPositions.add((cnoise0 / (cnoise0 - cnoise1)) * axis + corner0)

  normal = normal.normalize
  var vertex = intersectionPositions.sum / intersectionPositions.len
  vertex -= 0.5
  vertex += localPosition
  result = some((vertex, normal))

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
    echo &"Chunk at {position} is outside of terrain generation range"
    return

  let noise = position.makeNoise
  for x in 0..<chunkSize:
    for y in 0..<chunkSize:
      for z in 0..<chunkSize:
        let localPosition = vec3(x, y, z)
        let vwn0 = noise.findVertex(localPosition)
        if vwn0.isNone:
          continue
        let (vertex0, normal0) = vwn0.get
        for (axis0, axis1) in axisPairs:
          let vwn1 = noise.findVertex(localPosition + axis0)
          if vwn1.isNone:
            continue
          let vwn2 = noise.findVertex(localPosition + axis0 + axis1)
          if vwn2.isNone:
            continue
          let vwn3 = noise.findVertex(localPosition + axis1)
          if vwn3.isNone:
            continue
          let
            (vertex1, normal1) = vwn1.get
            (vertex2, normal2) = vwn2.get
            (vertex3, normal3) = vwn3.get
            axis2 = axis0.cross(axis1)
            sumVertexNormals = normal0 + normal1 + normal2 + normal3
          var orderedVertices =
            if sumVertexNormals.dot(axis2.toFloat32) < 0f:
              [vertex0, vertex3, vertex2, vertex1]
            else:
              [vertex0, vertex1, vertex2, vertex3]
          let midpoint = orderedVertices.sum / orderedVertices.len
          var surfaceNormal: Vec3[float32]
          for i in 0..<len(orderedVertices):
            let vertexA = orderedVertices[i]
            let vertexB = orderedVertices[floorMod(i+1, orderedVertices.len)]
            let vectorMA = vertexA - midpoint
            let vectorMB = vertexB - midpoint
            surfaceNormal += vectorMA.cross(vectorMB)

          surfaceNormal = surfaceNormal.normalize

          var walkPosition: Option[Vec3[float32]]
          if axis2.z == 1:
            # Determine if the surface can be walked on, and its elevation
            # within the cell column
            let normDotUp = surfaceNormal.dot(upVector).clamp(-1f, 1f)
            let incline = normDotUp.arccos
            if incline <= maxWalkableIncline:
              # https://en.wikipedia.org/wiki/Line%E2%80%93plane_intersection
              let l0 = localPosition + vec3(0.5f, 0.5f, 0f)
              let d = surfaceNormal.dot(midpoint - l0) / normDotUp
              walkPosition = some(l0 + d * upVector)

          var surface = TerrainSurface(
            vertices: orderedVertices,
            normal: surfaceNormal,
            walkPosition: walkPosition,
          )
          result.terrainSurfaces.add(surface)

  let endTime = getMonoTime()
  echo &"Chunk at {position} initialized in {endTime - beginTime}"

type GameEngine* = ref object
  chunks*: Table[Vec3[int], Chunk]
  playerChunk*: Chunk
  playerSurface*: TerrainSurface

proc chunk(self: GameEngine, position: Vec3[int]): Chunk =
  let alignedPosition = position - position.floorMod(chunkSize)
  result = self.chunks.getOrDefault(alignedPosition)
  if result == nil:
    result = newChunk(alignedPosition)
    self.chunks[alignedPosition] = result

proc chunk(self: GameEngine, x, y, z: int): Chunk =
  self.chunk(vec3(x, y, z))

proc newGameEngine*(): GameEngine =
  let beginTime = getMonoTime()
  new result
  var (x, y, z) = (0, 0, terrainHeightMultiplier)
  block findPosition:
    while true:
      doAssert z >= -terrainHeightMultiplier
      var chunk = result.chunk(x, y, z)
      for surface in chunk.terrainSurfaces:
        if surface.walkPosition.isSome:
          result.playerChunk = chunk
          result.playerSurface = surface
          break findPosition
      z -= chunkSize

  # Eager load the 125 chunks around the player's position
  for x in -2..2:
    for y in -2..2:
      for z in -2..2:
        discard result.chunk(vec3(x, y, z) * chunkSize +
                             result.playerChunk.position)

  let endTime = getMonoTime()
  echo &"{result.chunks.len} chunks initialized in {endTime - beginTime}"

proc attemptMove*(self: GameEngine, direction: Vec3[int]): bool =
  let maxDiffZ = direction.toFloat32.length
  var currentCell = self.playerChunk.position
  let currentWalkPosition = self.playerSurface.walkPosition.get
  currentCell.x += currentWalkPosition.x.int
  currentCell.y += currentWalkPosition.y.int
  currentCell.z += currentWalkPosition.z.int
  var candidateChunks = @[self.chunk(currentCell + direction)]
  for z in [-2, 2]:
    let candidateChunk = self.chunk(currentCell + direction + vec3(0, 0, z))
    if candidateChunk != candidateChunks[0]:
      candidateChunks.add(candidateChunk)
  let targetX = (currentCell + direction).x
  let targetY = (currentCell + direction).y
  for chunk in candidateChunks:
    for surface in chunk.terrainSurfaces:
      if surface.walkPosition.isNone:
        continue
      var candidateCell = chunk.position
      let candidateWalkPosition = surface.walkPosition.get
      candidateCell.x += candidateWalkPosition.x.int
      candidateCell.y += candidateWalkPosition.y.int
      candidateCell.z += candidateWalkPosition.z.int
      if candidateCell.x != targetX or candidateCell.y != targetY:
        continue
      let diffZ = (chunk.position - self.playerChunk.position +
                   candidateWalkPosition - currentWalkPosition).z.abs
      if diffZ <= maxDiffZ:
        self.playerChunk = chunk
        self.playerSurface = surface
        return true
