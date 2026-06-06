# Aula 6 - Phong com múltiplas luzes dinâmicas
#
# Controles:
#   W / A / S / D   → mover câmera
#   Mouse           → girar câmera
#   ESC             → fechar
#   SPACE           → alternar wireframe
#   1 / 2 / 3       → ligar/desligar luz vermelha / verde / azul
#   P               → pausar/retomar animação

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import os

WIDTH, HEIGHT        = 800, 600
window               = None
shader_program       = None
time_between_frames  = 0.0
scene_time           = 0.0

fps_counter          = 0
fps_time_accumulator = 0.0
fps                  = 0

cam_pos              = np.array([0.0, 1.0, 5.0], dtype=np.float32)
cam_pitch, cam_yaw   = 0.0, -90.0
cam_speed            = 5.0
last_x, last_y       = WIDTH / 2, HEIGHT / 2
first_mouse          = True

sphere_vao           = None
sphere_vertex_count  = 0

# Atenuação: [kc, kl, kq] — alcance curto / médio / longo
NUM_LIGHTS = 3

light_colors = np.array([
    [1.0,  0.15, 0.15],
    [0.15, 1.0,  0.15],
    [0.15, 0.35, 1.0 ],
], dtype=np.float32)

light_attenuation = np.array([
    [1.0, 0.35,  1.40  ],
    [1.0, 0.14,  0.07  ],
    [1.0, 0.045, 0.0016],
], dtype=np.float32)

light_positions = np.zeros((NUM_LIGHTS, 3), dtype=np.float32)
light_active    = [True, True, True]

is_wireframe     = False
animation_paused = False
cd_key           = 0.25
last_input_time  = 0.0


# VBO: [x, y, z, nx, ny, nz] por vértice, sem EBO
def build_sphere(rings=48, sectors=64, radius=1.0):
    vertices = []

    for r in range(rings):
        for s in range(sectors):
            theta0 = np.pi * r       / rings
            theta1 = np.pi * (r + 1) / rings
            phi0   = 2 * np.pi * s       / sectors
            phi1   = 2 * np.pi * (s + 1) / sectors

            def vtx(th, ph):
                nx = np.sin(th) * np.cos(ph)
                ny = np.cos(th)
                nz = np.sin(th) * np.sin(ph)
                return np.array([nx * radius, ny * radius, nz * radius,
                                  nx,          ny,          nz         ], dtype=np.float32)

            v00 = vtx(theta0, phi0)
            v01 = vtx(theta0, phi1)
            v10 = vtx(theta1, phi0)
            v11 = vtx(theta1, phi1)

            vertices.extend(v00); vertices.extend(v10); vertices.extend(v11)
            vertices.extend(v00); vertices.extend(v11); vertices.extend(v01)

    return np.array(vertices, dtype=np.float32)


def sphere_init():
    global sphere_vao, sphere_vertex_count

    data = build_sphere(rings=48, sectors=64, radius=1.0)
    sphere_vertex_count = len(data) // 6

    sphere_vao = glGenVertexArrays(1)
    glBindVertexArray(sphere_vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)

    stride = 6 * data.itemsize
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * data.itemsize))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)
    print(f"[ESFERA] {sphere_vertex_count} vértices, {sphere_vertex_count // 3} triângulos")


def update_light_positions(t):
    global light_positions

    # Luz 0: órbita horizontal (XZ)
    r0 = 2.5
    light_positions[0] = [
        r0 * np.cos(t * 0.8),
        0.5,
        r0 * np.sin(t * 0.8)
    ]

    # Luz 1: órbita vertical inclinada 45°
    r1    = 2.0
    a1    = t * 1.6
    cos45 = np.cos(np.radians(45))
    sin45 = np.sin(np.radians(45))
    light_positions[1] = [
        r1 * np.sin(a1) * cos45,
        r1 * np.sin(a1) * sin45,
        r1 * np.cos(a1)
    ]

    # Luz 2: Lissajous (fx=0.5, fy=1.0)
    r2 = 3.5
    light_positions[2] = [
        r2 * np.sin(t * 0.5),
        r2 * np.sin(t * 1.0) * 0.6,
        1.5
    ]


def openGL_init():
    global window

    glfw.init()
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(WIDTH, HEIGHT, "Aula 6 - Phong: Múltiplas Luzes Dinâmicas", None, None)
    if not window:
        print("Falha ao criar janela GLFW")
        glfw.terminate()
        exit()

    glfw.make_context_current(window)
    glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(window, mouse_callback)


def shaders_init():
    global shader_program

    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_pos;
        layout(location = 1) in vec3 vertex_normal;

        uniform mat4 transform, view, proj;

        out vec3 frag_pos;
        out vec3 world_normal;

        void main() {
            vec4 world_pos = transform * vec4(vertex_pos, 1.0);
            frag_pos       = world_pos.xyz;
            world_normal   = mat3(transpose(inverse(transform))) * vertex_normal;
            gl_Position    = proj * view * world_pos;
        }
    """

    fragment_shader = """
        #version 400

        #define NUM_LIGHTS 3

        in  vec3 frag_pos;
        in  vec3 world_normal;
        out vec4 frag_colour;

        uniform vec3  mat_color;
        uniform float mat_shininess;

        uniform vec3 cam_pos;

        uniform vec3 light_pos[NUM_LIGHTS];
        uniform vec3 light_color[NUM_LIGHTS];
        uniform vec3 light_att[NUM_LIGHTS];    // (kc, kl, kq)
        uniform int  light_active[NUM_LIGHTS];

        void main() {
            vec3 N = normalize(world_normal);
            vec3 V = normalize(cam_pos - frag_pos);

            vec3 result = vec3(0.0);

            for (int i = 0; i < NUM_LIGHTS; i++) {
                if (light_active[i] == 0) continue;

                vec3  L    = normalize(light_pos[i] - frag_pos);
                float dist = length(light_pos[i] - frag_pos);

                float kc  = light_att[i].x;
                float kl  = light_att[i].y;
                float kq  = light_att[i].z;
                float att = 1.0 / (kc + kl * dist + kq * dist * dist);

                vec3 ambient = 0.04 * light_color[i] * mat_color;

                float diff   = max(dot(N, L), 0.0);
                vec3 diffuse = diff * light_color[i] * mat_color;

                vec3  R    = reflect(-L, N);
                float spec = pow(max(dot(R, V), 0.0), mat_shininess);
                vec3 specular = spec * light_color[i];

                result += ambient + att * (diffuse + specular);
            }

            result = clamp(result, 0.0, 1.0);
            frag_colour = vec4(result, 1.0);
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    fs = OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    shader_program = OpenGL.GL.shaders.compileProgram(vs, fs)
    glDeleteShader(vs)
    glDeleteShader(fs)


def get_front_vector():
    return np.array([
        np.cos(np.radians(cam_yaw)) * np.cos(np.radians(cam_pitch)),
        np.sin(np.radians(cam_pitch)),
        np.sin(np.radians(cam_yaw)) * np.cos(np.radians(cam_pitch))
    ], dtype=np.float32)


def visualization_matrix_init():
    front = get_front_vector(); front /= np.linalg.norm(front)
    up    = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    f = front
    s = np.cross(f, up); s /= np.linalg.norm(s)
    u = np.cross(s, f)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] =  s
    view[1, :3] =  u
    view[2, :3] = -f
    view[0,  3] = -np.dot(s, cam_pos)
    view[1,  3] = -np.dot(u, cam_pos)
    view[2,  3] =  np.dot(f, cam_pos)

    glUniformMatrix4fv(glGetUniformLocation(shader_program, "view"), 1, GL_TRUE, view)


def projection_matrix_init():
    znear   = 0.1
    zfar    = 100.0
    fov     = np.radians(67.0)
    aspecto = WIDTH / HEIGHT

    a = 1.0 / (np.tan(fov / 2) * aspecto)
    b = 1.0 /  np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)

    proj = np.array([
        [a, 0,  0,  0],
        [0, b,  0,  0],
        [0, 0,  c,  d],
        [0, 0, -1,  0]
    ], dtype=np.float32)

    glUniformMatrix4fv(glGetUniformLocation(shader_program, "proj"), 1, GL_TRUE, proj)


def cam_init():
    visualization_matrix_init()
    projection_matrix_init()
    glUniform3fv(glGetUniformLocation(shader_program, "cam_pos"), 1, cam_pos)


def upload_lights():
    for i in range(NUM_LIGHTS):
        glUniform3fv(glGetUniformLocation(shader_program, f"light_pos[{i}]"),
                     1, light_positions[i].astype(np.float32))
        glUniform3fv(glGetUniformLocation(shader_program, f"light_color[{i}]"),
                     1, light_colors[i])
        glUniform3fv(glGetUniformLocation(shader_program, f"light_att[{i}]"),
                     1, light_attenuation[i])
        glUniform1i(glGetUniformLocation(shader_program, f"light_active[{i}]"),
                    1 if light_active[i] else 0)


def translation_matrix(tx, ty, tz):
    m = np.identity(4, dtype=np.float32)
    m[0, 3] = tx
    m[1, 3] = ty
    m[2, 3] = tz
    return m


def mouse_callback(win, xpos, ypos):
    global last_x, last_y, first_mouse, cam_pitch, cam_yaw

    if first_mouse:
        last_x, last_y = xpos, ypos
        first_mouse    = False

    x_off = xpos - last_x
    y_off = last_y - ypos
    last_x, last_y = xpos, ypos

    sens       = 0.1
    cam_yaw   += x_off * sens
    cam_pitch += y_off * sens
    cam_pitch  = max(-89.0, min(89.0, cam_pitch))


def keyboard_handler():
    global cam_pos, is_wireframe, last_input_time, light_active, animation_paused

    speed = cam_speed * time_between_frames
    front = get_front_vector(); front /= np.linalg.norm(front)
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

    now = glfw.get_time()
    if now - last_input_time > cd_key:

        if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
            is_wireframe = not is_wireframe
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if is_wireframe else GL_FILL)
            last_input_time = now

        if glfw.get_key(window, glfw.KEY_1) == glfw.PRESS:
            light_active[0] = not light_active[0]
            print(f"\n[LUZ 1 - vermelha] {'ON' if light_active[0] else 'OFF'}")
            last_input_time = now

        if glfw.get_key(window, glfw.KEY_2) == glfw.PRESS:
            light_active[1] = not light_active[1]
            print(f"\n[LUZ 2 - verde   ] {'ON' if light_active[1] else 'OFF'}")
            last_input_time = now

        if glfw.get_key(window, glfw.KEY_3) == glfw.PRESS:
            light_active[2] = not light_active[2]
            print(f"\n[LUZ 3 - azul    ] {'ON' if light_active[2] else 'OFF'}")
            last_input_time = now

        if glfw.get_key(window, glfw.KEY_P) == glfw.PRESS:
            animation_paused = not animation_paused
            print(f"\n[ANIMAÇÃO] {'PAUSADA' if animation_paused else 'RODANDO'}")
            last_input_time = now


def fps_calculation():
    global fps_counter, fps_time_accumulator, fps
    fps_counter          += 1
    fps_time_accumulator += time_between_frames
    if fps_time_accumulator >= 1.0:
        fps                   = fps_counter
        fps_counter           = 0
        fps_time_accumulator -= 1.0


def build_title():
    def state(i): return "ON" if light_active[i] else "OFF"
    wire = "Wire:ON" if is_wireframe else "Wire:OFF"
    anim = "Anim:PAUSE" if animation_paused else "Anim:ON"
    return (f"FPS:{fps} | "
            f"L1(vm):{state(0)} L2(vd):{state(1)} L3(az):{state(2)} | "
            f"{wire} | {anim}")


def render_init():
    global time_between_frames, scene_time

    last_frame_time = glfw.get_time()
    glEnable(GL_DEPTH_TEST)

    print_controls()

    while not glfw.window_should_close(window):
        current             = glfw.get_time()
        time_between_frames = current - last_frame_time
        last_frame_time     = current

        if not animation_paused:
            scene_time += time_between_frames

        fps_calculation()
        keyboard_handler()
        update_light_positions(scene_time)

        glClearColor(0.08, 0.08, 0.10, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(shader_program)

        cam_init()

        glUniform3fv(glGetUniformLocation(shader_program, "mat_color"), 1,
                     np.array([0.75, 0.75, 0.75], dtype=np.float32))
        glUniform1f(glGetUniformLocation(shader_program, "mat_shininess"), 64.0)

        upload_lights()

        glUniformMatrix4fv(
            glGetUniformLocation(shader_program, "transform"),
            1, GL_TRUE, translation_matrix(0.0, 0.0, 0.0)
        )
        glBindVertexArray(sphere_vao)
        glDrawArrays(GL_TRIANGLES, 0, sphere_vertex_count)

        glfw.set_window_title(window, build_title())
        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


def print_controls():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\n======= AULA 6 — Phong: Múltiplas Luzes Dinâmicas =======\n")
    print("Câmera:")
    print("  W / A / S / D  → mover câmera (FPS)")
    print("  Mouse          → girar câmera")
    print("  ESC            → fechar\n")
    print("Renderização:")
    print("  SPACE          → alternar wireframe")
    print("  P              → pausar/retomar animação das luzes\n")
    print("Luzes (toggle individual):")
    print("  1  → Luz vermelha  | órbita horizontal lenta  | alcance curto")
    print("  2  → Luz verde     | órbita vertical rápida   | alcance médio")
    print("  3  → Luz azul      | figura-8 lenta           | alcance longo\n")
    print("==========================================================\n")


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    openGL_init()
    shaders_init()
    sphere_init()
    render_init()