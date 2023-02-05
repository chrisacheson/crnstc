"""Module containing all user interface code."""
import ctypes

import glfw
from glfw import GLFW
import numpy as np
from OpenGL import GL as gl
from OpenGL.GL import shaders as glsl

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

        # x, y, z, r, g, b
        vertices = (0.0, 1.0, 0.0, 1.0, 0.0, 0.0,
                    1.0, -1.0, 0.0, 0.0, 1.0, 0.0,
                    -1.0, -1.0, 0.0, 0.0, 0.0, 1.0)
        vertex_elements = 6
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
        gl.glVertexAttribPointer(0, self.vertex_count, gl.GL_FLOAT,
                                 gl.GL_FALSE, stride, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(1)
        color_pointer = ctypes.c_void_p(self.vertex_count * element_bytes)
        gl.glVertexAttribPointer(1, self.vertex_count, gl.GL_FLOAT,
                                 gl.GL_FALSE, stride, color_pointer)

        with (defs.SHADERS_PATH / "vertex.glsl").open("r") as f:
            vertex_src = f.readlines()

        with (defs.SHADERS_PATH / "fragment.glsl").open("r") as f:
            fragment_src = f.readlines()

        self.shader = glsl.compileProgram(
            glsl.compileShader(vertex_src, gl.GL_VERTEX_SHADER),
            glsl.compileShader(fragment_src, gl.GL_FRAGMENT_SHADER),
        )
        gl.glUseProgram(self.shader)

    def render(self):
        glfw.poll_events()
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glBindVertexArray(self.vao)
        gl.glUseProgram(self.shader)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.vertex_count)
        gl.glFlush()
        glfw.swap_buffers(self.window)

    def quit(self):
        gl.glDeleteVertexArrays(1, (self.vao,))
        gl.glDeleteBuffers(1, (self.vbo,))
        glfw.terminate()

    @property
    def quit_requested(self):
        return glfw.window_should_close(self.window)
