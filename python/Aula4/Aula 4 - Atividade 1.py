import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import os


# General Configurations
WIDTH, HEIGHT        = 800, 600
window               = None
shader_program       = None
time_between_frames  = 0.0

fps_counter          = 0
fps_time_accumulator = 0.0
fps                  = 0

# Camera
cam_pos                  = np.array([0., 1., 5.], dtype=np.float32)
cam_pitch, cam_yaw       = 0.0, -90.0
cam_yaw_speed, cam_speed = 30.0, 5.0
last_x, last_y           = WIDTH / 2, HEIGHT / 2
first_mouse              = True

# VAO Cilinder 1
cilinder_vao1           = None
cilinder1_indices_count = 0
rad_segments_1          = 35
height_segments_1       = 5


# VAO Cilinder 2
cilinder_vao2           = None
cilinder2_indices_count = 0
rad_segments_2          = 5
height_segments_2       = 35

h, r                   = 2.0, 1.0

# Inputs
show_cilinder_1 = True
show_cilinder_2 = True
is_wireframe = False
cd_key = .3
last_input_time = 0.0


def build_cilinder(segments_rad, segments_height):
    vertices = []

    for j in range(segments_height + 1):
        y = -h/2 + j * (h / segments_height)
        # Loop radial (i)
        for i in range(segments_rad + 1):
            theta = i * (2 * np.pi / segments_rad)
            x = r * np.cos(theta)
            z = r * np.sin(theta)

            nx = np.cos(theta)
            nz = np.sin(theta)
            ny = 0.0

            vertices.extend([x, y, z, nx, ny, nz])
    return np.array(vertices, dtype=np.float32)


def connect_vertices(segments_rad, segments_height):
    ebo = []
    stride = segments_rad + 1
    
    for j in range(segments_height):
        for i in range(segments_rad):
            p1 = j * stride + i
            p2 = (j + 1) * stride + i
            p3 = j * stride + (i + 1)
            p4 = (j + 1) * stride + (i + 1)

            ebo.extend([p1, p2, p3])
            ebo.extend([p2, p4, p3])
            
    return np.array(ebo, dtype=np.uint32)


def cilinder_init():
    global cilinder_vao1, cilinder_vao2, cilinder1_indices_count, cilinder2_indices_count

    cilinder1_vertices = build_cilinder(rad_segments_1, height_segments_1)
    cilinder1_indices = connect_vertices(rad_segments_1, height_segments_1)
    cilinder1_indices_count = len(cilinder1_indices)

    cilinder2_vertices = build_cilinder(rad_segments_2, height_segments_2)
    cilinder2_indices = connect_vertices(rad_segments_2, height_segments_2)
    cilinder2_indices_count = len(cilinder2_indices)

    cilinder_vao1 = glGenVertexArrays(1)
    cilinder_vao2 = glGenVertexArrays(1)

    vbo = glGenBuffers(1)
    ebo = glGenBuffers(1)

    # VAO 1
    cilinder_vao1 = glGenVertexArrays(1)
    vbo1 = glGenBuffers(1)
    ebo1 = glGenBuffers(1)

    glBindVertexArray(cilinder_vao1)

    glBindBuffer(GL_ARRAY_BUFFER, vbo1)
    glBufferData(GL_ARRAY_BUFFER, cilinder1_vertices.nbytes, cilinder1_vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo1)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, cilinder1_indices.nbytes, cilinder1_indices, GL_STATIC_DRAW)

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * cilinder1_vertices.itemsize, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * cilinder1_vertices.itemsize, ctypes.c_void_p(3 * cilinder1_vertices.itemsize))
    glEnableVertexAttribArray(1)


    # VAO 2
    cilinder_vao2 = glGenVertexArrays(1)
    vbo2 = glGenBuffers(1)
    ebo2 = glGenBuffers(1)

    glBindVertexArray(cilinder_vao2)

    glBindBuffer(GL_ARRAY_BUFFER, vbo2)
    glBufferData(GL_ARRAY_BUFFER, cilinder2_vertices.nbytes, cilinder2_vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo2)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, cilinder2_indices.nbytes, cilinder2_indices, GL_STATIC_DRAW)

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * cilinder2_vertices.itemsize, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * cilinder2_vertices.itemsize, ctypes.c_void_p(3 * cilinder2_vertices.itemsize))
    glEnableVertexAttribArray(1)


def mouse_callback(window, xpos, ypos):
    global last_x, last_y, first_mouse, cam_pitch, cam_yaw

    if first_mouse:
        last_x, last_y = xpos, ypos
        first_mouse    = False

    x_offset = xpos - last_x
    y_offset = last_y - ypos
    last_x, last_y = xpos, ypos

    sensibility = 0.1
    cam_yaw   += x_offset * sensibility
    cam_pitch += y_offset * sensibility

    cam_pitch = max(-89.0, min(89.0, cam_pitch)) 


def keyboard_handler():
    global cam_pos, is_wireframe, last_input_time, show_cilinder_1, show_cilinder_2


    # Movement
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

    # End Movement

    # Other Inputs
    if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(window, True)

    if glfw.get_time() - last_input_time > cd_key:  
        if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
            is_wireframe = not is_wireframe
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if is_wireframe else GL_FILL)
            last_input_time = glfw.get_time()
        
        if glfw.get_key(window, glfw.KEY_1) == glfw.PRESS:
            show_cilinder_1 = not show_cilinder_1
            last_input_time = glfw.get_time()
        
        if glfw.get_key(window, glfw.KEY_2) == glfw.PRESS:
            show_cilinder_2 = not show_cilinder_2
            last_input_time = glfw.get_time()


def translation_matrix(tx, ty, tz):
    m = np.identity(4, dtype=np.float32)
    m[0, 3] = tx
    m[1, 3] = ty
    m[2, 3] = tz
    return m


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
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        layout(location = 1) in vec3 vertex_normal;
        
        uniform mat4 transform, view, proj;
        out vec3 world_normal;

        void main () {
            gl_Position  = proj * view * transform * vec4(vertex_posicao, 1.0);
            
            world_normal = mat3(transform) * vertex_normal;
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    if not glGetShaderiv(vs, GL_COMPILE_STATUS):
        print("Erro no vertex shader:\n", glGetShaderInfoLog(vs, 512, None))

    # Especificação do Fragment Shader:
    fragment_shader = """
        #version 400
        in  vec3 world_normal;
        out vec4 frag_colour;
        uniform vec4 colorobject;
        uniform vec3 light_dir = normalize(vec3(1.0, 1.0, 1.0));  

        void main () {            
            vec3  normal     = normalize(world_normal);
            float diffuse    = max(dot(normal, light_dir), 0.0);
            float ambient    = 0.2;
            float intensity  = diffuse + ambient;
            frag_colour      = vec4(colorobject.rgb * intensity, colorobject.a);
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
    front /= np.linalg.norm(front)

    center = cam_pos + front
    up   = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    f = center - cam_pos;  f /= np.linalg.norm(f)
    s = np.cross(f, up); s /= np.linalg.norm(s)
    u = np.cross(s, f)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] =  s
    view[1, :3] =  u
    view[2, :3] = -f
    view[0,  3] = -np.dot(s, cam_pos)
    view[1,  3] = -np.dot(u, cam_pos)
    view[2,  3] =  np.dot(f, cam_pos)

    transformLoc = glGetUniformLocation(shader_program, "view")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, view)


def projection_matrix_init():
    znear   = 0.1             # recorte z-near
    zfar    = 100.0           # recorte z-far
    fov     = np.radians(67.0)  # campo de visão
    aspecto = WIDTH / HEIGHT    # aspecto da janela

    a = 1.0 / (np.tan(fov / 2) * aspecto)
    b = 1.0 /  np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)

    projecao = np.array([
        [a,   0.0, 0.0,  0.0],
        [0.0, b,   0.0,  0.0],
        [0.0, 0.0, c,    d  ],
        [0.0, 0.0, -1.0, 0.0]
    ], dtype=np.float32)

    transformLoc = glGetUniformLocation(shader_program, "proj")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, projecao)


def cam_init():
    visualization_matrix_init()
    projection_matrix_init()


def color_define(r, g, b, a):
    color     = np.array([r, g, b, a], dtype=np.float32)
    color_loc = glGetUniformLocation(shader_program, "colorobject")
    glUniform4fv(color_loc, 1, color)


def fps_calculation():
    global fps_counter, fps_time_accumulator, fps

    fps_counter += 1
    fps_time_accumulator += time_between_frames

    if fps_time_accumulator >= 1.0:
        fps = fps_counter
        fps_counter = 0
        fps_time_accumulator -= 1.0


def get_mode_text():
    if show_cilinder_1 and show_cilinder_2:
        return "Cilindros 1 e 2"
    elif show_cilinder_1:
        return "Cilindro 1"
    elif show_cilinder_2:
        return "Cilindro 2"
    else:
        return "Nenhum Cilindro"


def get_wireframe_text():
    return "Wireframe: ON" if is_wireframe else "Wireframe: OFF"


def render_init():
    global time_between_frames, last_frame_time
    last_frame_time = glfw.get_time()
    glEnable(GL_DEPTH_TEST)

    print_controls()

    while not glfw.window_should_close(window):
        current_frame_time = glfw.get_time()
        time_between_frames = current_frame_time - last_frame_time
        last_frame_time = current_frame_time

        fps_calculation()
        keyboard_handler()

        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(shader_program)
        cam_init()

        # Desenha o Cilindro
        if show_cilinder_1:
            color_define(0.8, 0.5, 0.2, 1.0)
            glUniformMatrix4fv(
                glGetUniformLocation(shader_program, "transform"),
                1, 
                GL_TRUE, 
                translation_matrix(0.0, 0.0, 0.0)
            )
            
            glBindVertexArray(cilinder_vao1)
            glDrawElements(GL_TRIANGLES, cilinder1_indices_count, GL_UNSIGNED_INT, None)
        
        if show_cilinder_2:
            color_define(0.2, 0.5, 0.8, 1.0)
            glUniformMatrix4fv(
                glGetUniformLocation(shader_program, "transform"),
                1, 
                GL_TRUE, 
                translation_matrix(3.0, 0.0, 0.0)
            )
            
            glBindVertexArray(cilinder_vao2)
            glDrawElements(GL_TRIANGLES, cilinder2_indices_count, GL_UNSIGNED_INT, None)

        title = f"FPS: {fps} | Modo: {get_mode_text()} | {get_wireframe_text()}"
        glfw.set_window_title(window, title)
        
        glfw.swap_buffers(window)
        glfw.poll_events()
    glfw.terminate()


def print_controls():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\n\n========= CONTROLES =========\n")
    
    print("Movimento:")
    print("  W / A / S / D  → mover câmera (FPS)")
    print("  Mouse          → girar câmera")
    print("  ESC            → fechar\n")
    
    print("Renderização:")
    print("  SPACE          → alternar Wireframe\n")

    print("  1              → mostrar/ocultar Cilindro 1")
    print("  2              → mostrar/ocultar Cilindro 2")
    print("\n=============================\n")


if __name__ == "__main__":
    openGL_init()
    shaders_init()
    cilinder_init()
    render_init()