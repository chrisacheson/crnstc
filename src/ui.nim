import std/[
  deques,
  math,
  options,
  sequtils,
  sugar,
  tables,
]

import glm
import nimgl/[glfw, opengl]
import stb_image/read as stbi

import engine
import glm_helper

const
  gameName = "Cyberpunk Roguelike (Name Subject to Change)"
  screenWidth = 800
  screenHeight = 600
  screenAspect = screenWidth / screenHeight

  vaSizes = [3, # vertexPos
             3, # vertexColor
             2, # vertexTexCoord
            ]
  vaNumValues = vaSizes.sum
  vaValueBytes = sizeof(float32)
  vaBytes = collect:
    for num in vaSizes: num * vaValueBytes
  vaOffsets = @[0].concat(vaBytes.cumsummed)
  vaStride = vaOffsets[^1]

type Mesh = ref object
  vao: GLuint
  vbo: GLuint
  vertexData: seq[float32]
  vertexCount: int

proc newMesh(): Mesh =
  new result
  glGenVertexArrays(1, result.vao.addr)
  glBindVertexArray(result.vao)
  glGenBuffers(1, result.vbo.addr)
  glBindBuffer(GL_ARRAY_BUFFER, result.vbo)
  for i, vaSize in vaSizes:
    glEnableVertexAttribArray(i.GLuint)
    glVertexAttribPointer(i.GLuint, vaSize.GLint, EGL_FLOAT, false,
                          vaStride.GLsizei, cast[pointer](vaOffsets[i]))

proc destroy(self: Mesh) =
  glDeleteVertexArrays(1, self.vao.addr)
  glDeleteBuffers(1, self.vbo.addr)

type ChunkMesh = ref object
  chunk: Chunk
  mesh: Mesh

proc newChunkMesh(chunk: Chunk): ChunkMesh =
  ChunkMesh(chunk: chunk, mesh: newMesh())

proc build(self: ChunkMesh) =
  const
    walkableColor = vec3(0f, 1f, 0f)
    unwalkableColor = vec3(1f, 0f, 0f)
    textureCoords = [[0f, 0f], [1f, 0f], [1f, 1f], [0f, 1f]]
  self.mesh.vertexData.setLen(0)
  for surface in self.chunk.terrainSurfaces:
    var color = if surface.walkPosition.isSome: walkableColor
                else: unwalkableColor
    for i in [0, 1, 2, 2, 3, 0]:
      self.mesh.vertexData.add(surface.vertices[i].arr)
      self.mesh.vertexData.add(color.arr)
      self.mesh.vertexData.add(textureCoords[i])

  self.mesh.vertexCount = self.mesh.vertexData.len div vaNumValues
  glBindVertexArray(self.mesh.vao)
  glBindBuffer(GL_ARRAY_BUFFER, self.mesh.vbo)
  var vertexDataPointer = if self.mesh.vertexData.len == 0: nil
                          else: self.mesh.vertexdata[0].addr
  glBufferData(GL_ARRAY_BUFFER, self.mesh.vertexData.len * vaValueBytes,
               vertexDataPointer, GL_STATIC_DRAW)

proc destroy(self: ChunkMesh) =
  self.mesh.destroy

type SpriteSheet = ref object of RootObj
  textureId: GLuint
  spriteWidth: int
  spriteHeight: int
  columns: int
  rows: int

proc newSpriteSheet(path: string, spriteWidth: int, spriteHeight: int,
                    columns: int, rows: int): SpriteSheet =
  var textureId: GLuint
  glGenTextures(1, textureId.addr)
  result = SpriteSheet(textureId: textureId,
                       spriteWidth: spriteWidth, spriteHeight: spriteHeight,
                       columns: columns, rows: rows)
  glBindTexture(GL_TEXTURE_2D, textureId)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT.GLint)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT.GLint)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                  GL_LINEAR_MIPMAP_LINEAR.GLint)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR.GLint)
  var width, height, numChannels: int
  let textureData = stbi.load(path, width, height, numChannels, stbi.RGBA)
  assert width >= spriteWidth * columns
  assert height >= spriteHeight * rows
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA.GLint, width.GLsizei, height.GLsizei,
               0, GL_RGBA, GL_UNSIGNED_BYTE, textureData[0].addr)
  glGenerateMipmap(GL_TEXTURE_2D)

proc destroy(self: SpriteSheet) =
  glDeleteTextures(1, self.textureId.addr)

type Sprite = ref object of RootObj
  mesh: Mesh
  sheet: SpriteSheet
  sheetColumn: int
  sheetRow: int

proc newSprite(sheet: SpriteSheet, column: int, row: int): Sprite =
  const
    color = vec3(0f, 0f, 1f)
    vertices = [vec3(0f, 0f, 0f), vec3(1f, 0f, 0f), vec3(1f, 1f, 0f),
                vec3(1f, 1f, 0f), vec3(0f, 1f, 0f), vec3(0f, 0f, 0f)]
  result = Sprite(mesh: newMesh(), sheet: sheet,
                  sheetColumn: column, sheetRow: row)
  for vertex in vertices:
    result.mesh.vertexData.add(vertex.arr)
    result.mesh.vertexData.add(color.arr)
    result.mesh.vertexData.add((vertex.x + column.float32) /
                               sheet.columns.float32)
    result.mesh.vertexData.add((float32(row + 1) - vertex.y) /
                               sheet.rows.float32)

  result.mesh.vertexCount = result.mesh.vertexData.len div vaNumValues
  glBindVertexArray(result.mesh.vao)
  glBindBuffer(GL_ARRAY_BUFFER, result.mesh.vbo)
  var vertexDataPointer = if result.mesh.vertexData.len == 0: nil
                          else: result.mesh.vertexdata[0].addr
  glBufferData(GL_ARRAY_BUFFER, result.mesh.vertexData.len * vaValueBytes,
               vertexDataPointer, GL_STATIC_DRAW)

proc newSprite(sheet: SpriteSheet, index: int): Sprite =
  sheet.newSprite(index.floorMod(sheet.columns), index div sheet.columns)

proc newSprite(sheet: SpriteSheet, character: char): Sprite =
  sheet.newSprite(character.ord)

type UserInterface = ref object
  gameEngine: GameEngine
  window: GLFWWindow
  terrainTextureId: GLuint
  shaderProgramId: GLuint
  modelMatrixLocation: GLint
  chunkMeshes: Table[Vec3[int], ChunkMesh]
  spriteSheet: SpriteSheet
  playerSprite: Sprite

proc quitRequested*(self: UserInterface): bool =
  result = self.window.windowShouldClose

type KeyInput = object
  key: int32
  mods: int32

var inputQueue = initDeque[KeyInput]()

proc keyCallback(window: GLFWWindow, key: int32, scancode: int32, action: int32,
                 mods: int32): void {.cdecl.} =
  if action == GLFW_PRESS or action == GLFW_REPEAT:
    inputQueue.addLast(KeyInput(key: key, mods: mods))

proc newUserInterface*(gameEngine: GameEngine): UserInterface =
  new result
  result.gameEngine = gameEngine
  assert glfwInit()

  glfwWindowHint(GLFWContextVersionMajor, 3)
  glfwWindowHint(GLFWContextVersionMinor, 3)
  glfwWindowHint(GLFWOpenglForwardCompat, GLFW_TRUE)
  glfwWindowHint(GLFWOpenglProfile, GLFW_OPENGL_CORE_PROFILE)
  glfwWindowHint(GLFWResizable, GLFW_FALSE)

  result.window = glfwCreateWindow(screenWidth, screenHeight, gameName)
  if result.window == nil:
    quit(-1)

  discard result.window.setKeyCallback(keyCallback)
  result.window.makeContextCurrent()
  assert glInit()

  glClearColor(1f, 1f, 1f, 1f)
  glEnable(GL_BLEND)
  glEnable(GL_DEPTH_TEST)
  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

  glGenTextures(1, result.terrainTextureId.addr)
  glBindTexture(GL_TEXTURE_2D, result.terrainTextureId)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT.GLint)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT.GLint)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                  GL_LINEAR_MIPMAP_LINEAR.GLint)
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR.GLint)
  var width, height, numChannels: int
  let textureData = stbi.load("assets/textures/16x16-square_outline.png",
                              width, height, numChannels, stbi.RGBA)
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA.GLint, width.GLsizei, height.GLsizei,
               0, GL_RGBA, GL_UNSIGNED_BYTE, textureData[0].addr)
  glGenerateMipmap(GL_TEXTURE_2D)

  result.spriteSheet = newSpriteSheet("assets/16x16-sb-ascii-bordered.png",
                                      16, 16, 16, 16)

  var success: GLint
  var message = newSeq[char](1024)

  let vertexShaderId = glCreateShader(GL_VERTEX_SHADER)
  let vertexShaderSrc = readFile("assets/shaders/vertex.glsl").cstring
  glShaderSource(vertexShaderId, 1, vertexShaderSrc.addr, nil)
  glCompileShader(vertexShaderId)
  glGetShaderiv(vertexShaderId, GL_COMPILE_STATUS, success.addr)
  if not success.bool:
    glGetShaderInfoLog(vertexShaderId, 1024, nil,
                       cast[cstring](message[0].addr))
    echo message
    quit(-1)

  let fragmentShaderId = glCreateShader(GL_FRAGMENT_SHADER)
  let fragmentShaderSrc = readFile("assets/shaders/fragment.glsl").cstring
  glShaderSource(fragmentShaderId, 1, fragmentShaderSrc.addr, nil)
  glCompileShader(fragmentShaderId)
  glGetShaderiv(fragmentShaderId, GL_COMPILE_STATUS, success.addr)
  if not success.bool:
    glGetShaderInfoLog(fragmentShaderId, 1024, nil,
                       cast[cstring](message[0].addr))
    echo message
    quit(-1)

  result.shaderProgramId = glCreateProgram()
  glAttachShader(result.shaderProgramId, vertexShaderId)
  glAttachShader(result.shaderProgramId, fragmentShaderId)
  glLinkProgram(result.shaderProgramId)
  glGetProgramiv(result.shaderProgramId, GL_LINK_STATUS, success.addr)
  if not success.bool:
    glGetProgramInfoLog(result.shaderProgramId, 1024, nil,
                        cast[cstring](message[0].addr))
    echo message
    quit(-1)

  glDeleteShader(vertexShaderId)
  glDeleteShader(fragmentShaderId)

  glUseProgram(result.shaderProgramId)
  glUniform1i(glGetUniformLocation(result.shaderProgramId, "imageTexture"), 0)

  var projectionTransform = perspective(fovy=radians(90f), aspect=screenAspect,
                                        zNear=0.1f, zFar=100f)
  glUniformMatrix4fv(glGetUniformLocation(result.shaderProgramId, "projection"),
                     1, false, projectionTransform.caddr)
  
  let cameraHeight = 0.5 * screenHeight / 16
  var viewTransform = lookAt(eye=vec3(0f, 0f, cameraHeight),
                             center=vec3(0f, 0f, 0f), up=vec3(0f, 1f, 0f))
  glUniformMatrix4fv(glGetUniformLocation(result.shaderProgramId, "view"), 1,
                     false, viewTransform.caddr)

  result.modelMatrixLocation = glGetUniformLocation(result.shaderProgramId,
                                                    "model")

  result.playerSprite = result.spriteSheet.newSprite('@')

const
  northVector = vec3(0, 1, 0)
  southVector = -northVector
  eastVector = vec3(1, 0, 0)
  westVector = -eastVector
  northeastVector = northVector + eastVector
  southeastVector = southVector + eastVector
  northwestVector = -southeastVector
  southwestVector = -northeastVector

proc handleInput*(self: UserInterface) =
  glfwPollEvents()
  while inputQueue.len > 0:
    var keyInput = inputQueue.popFirst
    if keyInput.key == GLFWKey.Escape:
      self.window.setWindowShouldClose(true)
    elif keyInput.key in [GLFWKey.Kp8, GLFWKey.Up, GLFWKey.K]:
      discard self.gameEngine.attemptMove(northVector)
    elif keyInput.key in [GLFWKey.Kp2, GLFWKey.Down, GLFWKey.J]:
      discard self.gameEngine.attemptMove(southVector)
    elif keyInput.key in [GLFWKey.Kp6, GLFWKey.Right, GLFWKey.L]:
      discard self.gameEngine.attemptMove(eastVector)
    elif keyInput.key in [GLFWKey.Kp4, GLFWKey.Left, GLFWKey.H]:
      discard self.gameEngine.attemptMove(westVector)
    elif keyInput.key in [GLFWKey.Kp9, GLFWKey.PageUp, GLFWKey.U]:
      discard self.gameEngine.attemptMove(northeastVector)
    elif keyInput.key in [GLFWKey.Kp3, GLFWKey.PageDown, GLFWKey.N]:
      discard self.gameEngine.attemptMove(southeastVector)
    elif keyInput.key in [GLFWKey.Kp7, GLFWKey.Home, GLFWKey.Y]:
      discard self.gameEngine.attemptMove(northwestVector)
    elif keyInput.key in [GLFWKey.Kp1, GLFWKey.End, GLFWKey.B]:
      discard self.gameEngine.attemptMove(southwestVector)

proc render*(self: UserInterface) =
  glClear(GL_COLOR_BUFFER_BIT or GL_DEPTH_BUFFER_BIT)
  glActiveTexture(GL_TEXTURE0)
  glBindTexture(GL_TEXTURE_2D, self.terrainTextureId)
  glUseProgram(self.shaderProgramId)

  for position, chunk in self.gameEngine.chunks:
    var chunkMesh = self.chunkMeshes.getOrDefault(position)
    if chunkMesh == nil:
      chunkMesh = chunk.newChunkMesh
      self.chunkMeshes[position] = chunkMesh
      chunkMesh.build

    glBindVertexArray(chunkMesh.mesh.vao)
    let walkPosition = (self.gameEngine.playerSurface.walkPosition.get +
                        self.gameEngine.playerChunk.position)
    let headPosition = walkPosition + vec3(0f, 0f, 1.8f)
    var relativePosition = position - headPosition
    var modelTransform = mat4(1f).translate(relativePosition)
    glUniformMatrix4fv(self.modelMatrixLocation, 1, false, modelTransform.caddr)
    glDrawArrays(GL_TRIANGLES, 0, chunkMesh.mesh.vertexCount.GLsizei)

  glBindTexture(GL_TEXTURE_2D, self.spriteSheet.textureId)
  glBindVertexArray(self.playerSprite.mesh.vao)
  var modelTransform = mat4(1f).translate(vec3(-0.5f, -0.5f, 0f))
  glUniformMatrix4fv(self.modelMatrixLocation, 1, false, modelTransform.caddr)
  glDrawArrays(GL_TRIANGLES, 0, self.playerSprite.mesh.vertexCount.GLsizei)

  glFlush()
  self.window.swapBuffers()

proc quit*(self: UserInterface) =
  for chunkMesh in self.chunkMeshes.values:
    chunkMesh.destroy
  self.playerSprite.mesh.destroy
  self.spriteSheet.destroy
  glDeleteTextures(1, self.terrainTextureId.addr)
  glDeleteProgram(self.shaderProgramId)
  self.window.destroyWindow
  glfwTerminate()
