import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np


# General Configurations

WIDTH               = 800
HEIGHT              = 600
window              = None
shader_program      = None

time_between_frames = 0.0

# Camera

cam_pos        = np.array([0., 2., 12.], dtype=np.float32)
cam_pitch      = -10.
cam_yaw        = -90.
cam_yaw_speed  = 30.
cam_speed      = 5.

last_x, last_y = WIDTH / 2, HEIGHT / 2
first_mouse    = True


# VAO
cilinder_vao = None
cilinder_rad = 0.5
cilinder_height = 1.0


def build_cilinder(segments_rad, segments_height):
    vertices = []
    for i in range(segments_height + 1):
        y = -cilinder_height / 2 + i * (cilinder_height / segments_height)
        for j in range(segments_rad + 1):
            theta = j * (2 * np.pi / segments_rad)
            x = cilinder_rad * np.cos(theta)
            z = cilinder_rad * np.sin(theta)
            vertices.extend([x, y, z])
    return np.array(vertices, dtype=np.float32)


def cilinder_init():
    pass


def mouse_callback(window, xpos, ypos):
    global last_x, last_y, first_mouse, cam_pitch, cam_yaw

    if first_mouse:
        last_x, last_y = xpos, ypos
        first_mouse = False

    x_offset = xpos - last_x
    y_offset = last_y - ypos

    last_x = xpos
    last_y = ypos

    cam_pitch += y_offset * cam_yaw_speed * time_between_frames
    cam_yaw   += x_offset * cam_yaw_speed * time_between_frames


def keyboard_handler():
    global cam_pos

    speed = cam_speed * time_between_frames

    front = np.array([
        np.cos(np.radians(cam_yaw)) * np.cos(np.radians(cam_pitch)),
        np.sin(np.radians(cam_pitch)),
        np.sin(np.radians(cam_yaw)) * np.cos(np.radians(cam_pitch))
    ], dtype=np.float32)
    front /= np.linalg.norm(front)

    right = np.cross(front, np.array([0.0, 1.0, 0.0], dtype=np.float32))
    right /= np.linalg.norm(right)

    if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        cam_pos += front * speed
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        cam_pos -= front * speed

    if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        cam_pos -= right * speed
    if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        cam_pos += right * speed

    if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(window, True)


def openGL_init():
    global window

    glfw.init()
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(WIDTH, HEIGHT, "Aula 4 - Atividade 1", None, None)
    if not window:
        print("Failed to create GLFW window")
        glfw.terminate()
        exit()
        return

    glfw.make_context_current(window)

    glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(window, mouse_callback)


def shaders_init():
    global shader_program

    vertex_shader = """
        #version 330 core
        layout(location = 0) in vec3 vertex_posicao;

        uniform mat4 transform, view, proj;
        void main() {
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    if not glGetShaderiv(vs, GL_COMPILE_STATUS):
        print("Erro no vertex shader:\n", glGetShaderInfoLog(vs, 512, None))

    # Especificação do Fragment Shader:
    fragment_shader = """
        #version 330 core
        out vec4 frag_colour;
        uniform vec4 colorobject;
        void main() {
            frag_colour = colorobject;
        }
    """
    fs = OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    if not glGetShaderiv(fs, GL_COMPILE_STATUS):
        print("Erro no fragment shader:\n", glGetShaderInfoLog(fs, 512, None))

    # Especificação do Shader Program:
    shader_program = OpenGL.GL.shaders.compileProgram(vs, fs)
    if not glGetProgramiv(shader_program, GL_LINK_STATUS):
        print("Erro na linkagem do shader:\n", glGetProgramInfoLog(shader_program, 512, None))

    glDeleteShader(vs)
    glDeleteShader(fs)


def visualization_matrix_init():
    front = np.array([
        np.cos(np.radians(cam_yaw)) * np.cos(np.radians(cam_pitch)),
        np.sin(np.radians(cam_pitch)),
        np.sin(np.radians(cam_yaw)) * np.cos(np.radians(cam_pitch))
    ], dtype=np.float32)
    front = front / np.linalg.norm(front)

    center = cam_pos + front
    up = np.array([0., 1., 0.], dtype=np.float32)

    f = (center - cam_pos) / np.linalg.norm(center - cam_pos)
    s = np.cross(f, up) / np.linalg.norm(np.cross(f, up))
    u = np.cross(s, f)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] =  s
    view[1, :3] =  u
    view[2, :3] = -f
    view[0,  3] = -np.dot(s, cam_pos)
    view[1,  3] = -np.dot(u, cam_pos)
    view[2,  3] =  np.dot(f, cam_pos)

    transform_loc = glGetUniformLocation(shader_program, "view")
    glUniformMatrix4fv(transform_loc, 1, GL_FALSE, view)


def projection_matrix_init():
    znear   = 0.1             
    zfar    = 100.0           
    fov     = np.radians(67.0)  
    aspect = WIDTH / HEIGHT    

    a = 1.0 / (np.tan(fov / 2) * aspect)
    b = 1.0 /  np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)

    projection = np.array([
        [a,   0.0, 0.0,  0.0],
        [0.0, b,   0.0,  0.0],
        [0.0, 0.0, c,    d  ],
        [0.0, 0.0, -1.0, 1.0]
    ], dtype=np.float32)

    transformLoc = glGetUniformLocation(shader_program, "proj")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, projection)


def cam_init():
    visualization_matrix_init()
    projection_matrix_init()


def color_define(r, g, b, a):
    color     = np.array([r, g, b, a], dtype=np.float32)
    color_loc = glGetUniformLocation(shader_program, "colorobject")
    glUniform4fv(color_loc, 1, color)


def render_init():
    global time_between_frames

    last_frame_time = glfw.get_time()

    glEnable(GL_DEPTH_TEST)

    while not glfw.window_should_close(window):
        current_frame_time = glfw.get_time()
        time_between_frames = current_frame_time - last_frame_time
        last_frame_time = current_frame_time

        keyboard_handler()

        glClearColor(0.2, 0.3, 0.3, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(shader_program)
        cam_init()

        # Aqui é onde os objetos seriam desenhados usando as funções de desenho

        glfw.swap_buffers(window)
        glfw.poll_events()
    glfw.terminate()

if __name__ == "__main__":
    openGL_init()
    shaders_init()
    render_init()