import std/[
  math,
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

type ChunkMesh = ref object
  chunk: Chunk
  vao: GLuint
  vbo: GLuint
  vertexData: seq[float32]
  vertexCount: int

const
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

proc newChunkMesh(chunk: Chunk): ChunkMesh =
  new result
  result.chunk = chunk

  glGenVertexArrays(1, result.vao.addr)
  glBindVertexArray(result.vao)
  glGenBuffers(1, result.vbo.addr)
  glBindBuffer(GL_ARRAY_BUFFER, result.vbo)
  for i, vaSize in vaSizes:
    glEnableVertexAttribArray(i.GLuint)
    glVertexAttribPointer(i.GLuint, vaSize.GLint, EGL_FLOAT, false,
                          vaStride.GLsizei, cast[pointer](vaOffsets[i]))

proc build(self: ChunkMesh) =
  const
    mainColor = vec3(0f, 1f, 0f)
    altColor = vec3(1f, 0f, 0f)
  self.vertexData.setLen(0)
  for cell, cellSurfaces in self.chunk.terrainSurfaces:
    var color = if cell.x == 0 and cell.y == 0: altColor else: mainColor
    for surface in cellSurfaces:
      var vertices = surface.vertices
      for vertex in vertices.mitems: vertex = vertex + cell
      while vertices.len >= 3:
        var upperVertexTextureCoordinateS = 0f
        if vertices.len == 3:
          upperVertexTextureCoordinateS = 1f
        elif vertices.len < surface.vertices.len:
          upperVertexTextureCoordinateS = 0.5

        self.vertexData.add(vertices[0].arr)
        self.vertexData.add(color.arr)
        self.vertexData.add([upperVertexTextureCoordinateS, 1f])
        self.vertexData.add(vertices[1].arr)
        self.vertexData.add(color.arr)
        self.vertexData.add([0f, 0f])
        self.vertexData.add(vertices[2].arr)
        self.vertexData.add(color.arr)
        self.vertexData.add([1f, 0f])
        vertices.delete(1)

  self.vertexCount = self.vertexData.len div vaNumValues
  glBindVertexArray(self.vao)
  glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
  var vertexDataPointer = if self.vertexData.len == 0: nil
                          else: self.vertexdata[0].addr
  glBufferData(GL_ARRAY_BUFFER, self.vertexData.len * vaValueBytes,
               vertexDataPointer, GL_STATIC_DRAW)

proc destroy(self: ChunkMesh) =
  glDeleteVertexArrays(1, self.vao.addr)
  glDeleteBuffers(1, self.vbo.addr)

type UserInterface = ref object
  gameEngine: GameEngine
  window: GLFWWindow
  textureId: GLuint
  shaderProgramId: GLuint
  modelMatrixLocation: GLint
  chunkMeshes: Table[Vec3[int], ChunkMesh]

proc quitRequested*(self: UserInterface): bool =
  result = self.window.windowShouldClose

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

  result.window.makeContextCurrent()
  assert glInit()

  glClearColor(1f, 1f, 1f, 1f)
  glEnable(GL_BLEND)
  glEnable(GL_DEPTH_TEST)
  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

  glGenTextures(1, result.textureId.addr)
  glBindTexture(GL_TEXTURE_2D, result.textureId)
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

proc render*(self: UserInterface) =
  glfwPollEvents()
  glClear(GL_COLOR_BUFFER_BIT or GL_DEPTH_BUFFER_BIT)
  glActiveTexture(GL_TEXTURE0)
  glBindTexture(GL_TEXTURE_2D, self.textureId)
  glUseProgram(self.shaderProgramId)

  for position, chunk in self.gameEngine.chunks:
    var mesh = self.chunkMeshes.getOrDefault(position)
    if mesh == nil:
      mesh = chunk.newChunkMesh
      self.chunkMeshes[position] = mesh
      mesh.build

    glBindVertexArray(mesh.vao)
    let relativePosition = position - self.gameEngine.playerPosition - 0.5f
    var modelTransform = mat4(1f).translate(relativePosition)
    glUniformMatrix4fv(self.modelMatrixLocation, 1, false, modelTransform.caddr)
    glDrawArrays(GL_TRIANGLES, 0, mesh.vertexCount.GLsizei)

  glFlush()
  self.window.swapBuffers()

proc quit*(self: UserInterface) =
  for mesh in self.chunkMeshes.values:
    mesh.destroy
  glDeleteTextures(1, self.textureId.addr)
  glDeleteProgram(self.shaderProgramId)
  self.window.destroyWindow
  glfwTerminate()
