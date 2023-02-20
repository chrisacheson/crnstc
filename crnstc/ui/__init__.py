"""Module containing all user interface code."""
import ctypes

import glfw
from glfw import GLFW
import numpy as np
from OpenGL import GL as gl
from OpenGL.GL import shaders as glsl
import PIL.Image
import pyrr

from crnstc import definitions as defs
from crnstc.engine import Chunk, GameEngine


class UserInterface:
    def __init__(self, game_engine: GameEngine):
        self.game_engine = game_engine
        self.chunk_meshes = dict()

        glfw.init()
        glfw.window_hint(GLFW.GLFW_CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(GLFW.GLFW_CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(GLFW.GLFW_OPENGL_PROFILE,
                         GLFW.GLFW_OPENGL_CORE_PROFILE)
        glfw.window_hint(GLFW.GLFW_OPENGL_FORWARD_COMPAT, GLFW.GLFW_TRUE)
        glfw.window_hint(GLFW.GLFW_DOUBLEBUFFER, GLFW.GLFW_TRUE)

        self.window = glfw.create_window(
            defs.SCREEN_WIDTH,
            defs.SCREEN_HEIGHT,
            "Cyberpunk Roguelike (Name Subject to Change)",
            None,
            None,
        )
        glfw.make_context_current(self.window)

        gl.glClearColor(0, 0, 0, 1)
        gl.glEnable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S,
                           gl.GL_REPEAT)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T,
                           gl.GL_REPEAT)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
                           gl.GL_LINEAR_MIPMAP_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
                           gl.GL_LINEAR)
        filepath = defs.TEXTURES_PATH / "16x16-square_outline.png"

        with PIL.Image.open(filepath, mode="r") as image:
            image_width, image_height = image.size
            image = image.convert("RGBA")
            image_data = image.tobytes()
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA,
                            image_width, image_height, 0, gl.GL_RGBA,
                            gl.GL_UNSIGNED_BYTE, image_data)

        gl.glGenerateMipmap(gl.GL_TEXTURE_2D)

        with (defs.SHADERS_PATH / "vertex.glsl").open("r") as f:
            vertex_src = f.readlines()

        with (defs.SHADERS_PATH / "fragment.glsl").open("r") as f:
            fragment_src = f.readlines()

        self.shader = glsl.compileProgram(
            glsl.compileShader(vertex_src, gl.GL_VERTEX_SHADER),
            glsl.compileShader(fragment_src, gl.GL_FRAGMENT_SHADER),
        )
        gl.glUseProgram(self.shader)
        gl.glUniform1i(gl.glGetUniformLocation(self.shader, "imageTexture"), 0)

        projection_transform = pyrr.matrix44.create_perspective_projection(
            fovy=90, aspect=defs.SCREEN_WIDTH/defs.SCREEN_HEIGHT,
            near=0.1, far=100, dtype=np.float32,
        )
        gl.glUniformMatrix4fv(
            gl.glGetUniformLocation(self.shader, "projection"),
            1, gl.GL_FALSE, projection_transform,
        )

        camera_height = 0.5 * defs.SCREEN_HEIGHT / 16
        view_transform = pyrr.matrix44.create_look_at(
            eye=(0, 0, camera_height),
            target=(0, 0, 0),
            up=(0, 1, camera_height),
            dtype=np.float32,
        )
        gl.glUniformMatrix4fv(gl.glGetUniformLocation(self.shader, "view"),
                              1, gl.GL_FALSE, view_transform)

        self.model_matrix_location = gl.glGetUniformLocation(self.shader,
                                                             "model")

    def render(self):
        glfw.poll_events()
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)
        gl.glUseProgram(self.shader)

        for position, chunk in self.game_engine.chunks.items():
            mesh = self.chunk_meshes.get(position)

            if not mesh:
                mesh = ChunkMesh(chunk)
                self.chunk_meshes[position] = mesh

            if mesh.vertices is None:
                mesh.build()

            gl.glBindVertexArray(mesh.vao)

            shift = np.array(chunk.position - self.game_engine.player_position,
                             dtype=np.float32)
            model_transform = pyrr.matrix44.create_identity(
                dtype=np.float32
            )
            model_transform = pyrr.matrix44.multiply(
                m1=model_transform,
                m2=pyrr.matrix44.create_from_translation(vec=shift,
                                                         dtype=np.float32),
            )

            gl.glUniformMatrix4fv(self.model_matrix_location, 1,
                                  gl.GL_FALSE, model_transform)
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, mesh.vertex_count)

        gl.glFlush()
        glfw.swap_buffers(self.window)

    def quit(self):
        for mesh in self.chunk_meshes.values():
            mesh.destroy()

        gl.glDeleteTextures(1, (self.texture,))
        glfw.terminate()

    @property
    def quit_requested(self):
        return glfw.window_should_close(self.window)


class ChunkMesh:
    color = (0.0, 1.0, 0.0)

    position_elements = 3
    color_elements = 3
    texture_elements = 2

    element_bytes = 4

    def __init__(self, chunk: Chunk):
        self.chunk = chunk
        self.vertices = None
        self.vertex_count = 0

        index = 0
        position_index = index
        index += self.position_elements
        color_index = index
        index += self.color_elements
        texture_index = index
        index += self.texture_elements
        self.vertex_elements = (self.position_elements + self.color_elements
                                + self.texture_elements)
        stride = self.vertex_elements * self.element_bytes

        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)
        self.vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glEnableVertexAttribArray(0)
        position_pointer = ctypes.c_void_p(position_index * self.element_bytes)
        gl.glVertexAttribPointer(0, self.position_elements, gl.GL_FLOAT,
                                 gl.GL_FALSE, stride, position_pointer)
        gl.glEnableVertexAttribArray(1)
        color_pointer = ctypes.c_void_p(color_index * self.element_bytes)
        gl.glVertexAttribPointer(1, self.color_elements, gl.GL_FLOAT,
                                 gl.GL_FALSE, stride, color_pointer)
        gl.glEnableVertexAttribArray(2)
        texture_pointer = ctypes.c_void_p(texture_index * self.element_bytes)
        gl.glVertexAttribPointer(2, self.texture_elements, gl.GL_FLOAT,
                                 gl.GL_FALSE, stride, texture_pointer)

    def build(self):
        self.vertices = list()
        cells = self.chunk.cells
        color = self.color

        for local, value in np.ndenumerate(cells):
            if value == 0:
                continue

            x, y, z = local

            if x == 0 or cells[x-1, y, z] == 0:
                face_x = x - 0.5  # west face
                self.vertices.extend((
                    face_x, y+0.5, z+0.5, *color, 0.0, 1.0,  # nwu
                    face_x, y+0.5, z-0.5, *color, 0.0, 0.0,  # nwd
                    face_x, y-0.5, z-0.5, *color, 1.0, 0.0,  # swd
                    face_x, y-0.5, z-0.5, *color, 1.0, 0.0,  # swd
                    face_x, y-0.5, z+0.5, *color, 1.0, 1.0,  # swu
                    face_x, y+0.5, z+0.5, *color, 0.0, 1.0,  # nwu
                ))

            if x == defs.CHUNK_SIZE - 1 or cells[x+1, y, z] == 0:
                face_x = x + 0.5  # east face
                self.vertices.extend((
                    face_x, y-0.5, z+0.5, *color, 0.0, 1.0,  # seu
                    face_x, y-0.5, z-0.5, *color, 0.0, 0.0,  # sed
                    face_x, y+0.5, z-0.5, *color, 1.0, 0.0,  # ned
                    face_x, y+0.5, z-0.5, *color, 1.0, 0.0,  # ned
                    face_x, y+0.5, z+0.5, *color, 1.0, 1.0,  # neu
                    face_x, y-0.5, z+0.5, *color, 0.0, 1.0,  # seu
                ))

            if y == 0 or cells[x, y-1, z] == 0:
                face_y = y - 0.5  # south face
                self.vertices.extend((
                    x-0.5, face_y, z+0.5, *color, 0.0, 1.0,  # swu
                    x-0.5, face_y, z-0.5, *color, 0.0, 0.0,  # swd
                    x+0.5, face_y, z-0.5, *color, 1.0, 0.0,  # sed
                    x+0.5, face_y, z-0.5, *color, 1.0, 0.0,  # sed
                    x+0.5, face_y, z+0.5, *color, 1.0, 1.0,  # seu
                    x-0.5, face_y, z+0.5, *color, 0.0, 1.0,  # swu
                ))

            if y == defs.CHUNK_SIZE - 1 or cells[x, y+1, z] == 0:
                face_y = y + 0.5  # north face
                self.vertices.extend((
                    x+0.5, face_y, z+0.5, *color, 0.0, 1.0,  # neu
                    x+0.5, face_y, z-0.5, *color, 0.0, 0.0,  # ned
                    x-0.5, face_y, z-0.5, *color, 1.0, 0.0,  # nwd
                    x-0.5, face_y, z-0.5, *color, 1.0, 0.0,  # nwd
                    x-0.5, face_y, z+0.5, *color, 1.0, 1.0,  # nwu
                    x+0.5, face_y, z+0.5, *color, 0.0, 1.0,  # neu
                ))

            if z == 0 or cells[x, y, z-1] == 0:
                face_z = z - 0.5  # bottom face
                self.vertices.extend((
                    x-0.5, y-0.5, face_z, *color, 0.0, 1.0,  # swd
                    x-0.5, y+0.5, face_z, *color, 0.0, 0.0,  # nwd
                    x+0.5, y+0.5, face_z, *color, 1.0, 0.0,  # ned
                    x+0.5, y+0.5, face_z, *color, 1.0, 0.0,  # ned
                    x+0.5, y-0.5, face_z, *color, 1.0, 1.0,  # sed
                    x-0.5, y-0.5, face_z, *color, 0.0, 1.0,  # swd
                ))

            if z == defs.CHUNK_SIZE - 1 or cells[x, y, z+1] == 0:
                face_z = z + 0.5  # top face
                self.vertices.extend((
                    x-0.5, y+0.5, face_z, *color, 0.0, 1.0,  # nwu
                    x-0.5, y-0.5, face_z, *color, 0.0, 0.0,  # swu
                    x+0.5, y-0.5, face_z, *color, 1.0, 0.0,  # seu
                    x+0.5, y-0.5, face_z, *color, 1.0, 0.0,  # seu
                    x+0.5, y+0.5, face_z, *color, 1.0, 1.0,  # neu
                    x-0.5, y+0.5, face_z, *color, 0.0, 1.0,  # nwu
                ))

        self.vertex_count = len(self.vertices) // self.vertex_elements
        self.vertices = np.array(self.vertices, dtype=np.float32)
        gl.glBindVertexArray(self.vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertices.nbytes,
                        self.vertices, gl.GL_STATIC_DRAW)

    def destroy(self):
        gl.glDeleteVertexArrays(1, (self.vao,))
        gl.glDeleteBuffers(1, (self.vbo,))
