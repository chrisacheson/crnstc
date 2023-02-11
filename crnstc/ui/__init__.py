"""Module containing all user interface code."""
import ctypes

import glfw
from glfw import GLFW
import numpy as np
from OpenGL import GL as gl
from OpenGL.GL import shaders as glsl
import PIL.Image

from crnstc import definitions as defs


class UserInterface:
    def __init__(self):
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
                           gl.GL_NEAREST_MIPMAP_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
                           gl.GL_NEAREST)
        filepath = defs.TEXTURES_PATH / "16x16-square_outline.png"

        with PIL.Image.open(filepath, mode="r") as image:
            image_width, image_height = image.size
            image = image.convert("RGBA")
            image_data = image.tobytes()
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA,
                            image_width, image_height, 0, gl.GL_RGBA,
                            gl.GL_UNSIGNED_BYTE, image_data)

        gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)

        # x, y, z, r, g, b, s, t
        vertices = (
            -0.5, 0.5, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0,
            0.5, 0.5, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0,
            -0.5, -0.5, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0,
            0.5, 0.5, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0,
            0.5, -0.5, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0,
            -0.5, -0.5, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0,
        )
        index = 0
        position_index = index
        position_elements = 3
        index += position_elements
        color_index = index
        color_elements = 3
        index += color_elements
        texture_index = index
        texture_elements = 2
        index += texture_elements
        vertex_elements = position_elements + color_elements + texture_elements
        element_bytes = 4
        stride = vertex_elements * element_bytes
        self.vertex_count = len(vertices) // vertex_elements
        vertices = np.array(vertices, dtype=np.float32)

        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)
        self.vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices,
                        gl.GL_STATIC_DRAW)
        gl.glEnableVertexAttribArray(0)
        position_pointer = ctypes.c_void_p(position_index * element_bytes)
        gl.glVertexAttribPointer(0, position_elements, gl.GL_FLOAT,
                                 gl.GL_FALSE, stride, position_pointer)
        gl.glEnableVertexAttribArray(1)
        color_pointer = ctypes.c_void_p(color_index * element_bytes)
        gl.glVertexAttribPointer(1, color_elements, gl.GL_FLOAT,
                                 gl.GL_FALSE, stride, color_pointer)
        gl.glEnableVertexAttribArray(2)
        texture_pointer = ctypes.c_void_p(texture_index * element_bytes)
        gl.glVertexAttribPointer(2, texture_elements, gl.GL_FLOAT,
                                 gl.GL_FALSE, stride, texture_pointer)

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

    def render(self):
        glfw.poll_events()
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glBindVertexArray(self.vao)
        gl.glUseProgram(self.shader)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.vertex_count)
        gl.glFlush()
        glfw.swap_buffers(self.window)

    def quit(self):
        gl.glDeleteVertexArrays(1, (self.vao,))
        gl.glDeleteBuffers(1, (self.vbo,))
        gl.glDeleteTextures(1, (self.texture,))
        glfw.terminate()

    @property
    def quit_requested(self):
        return glfw.window_should_close(self.window)
