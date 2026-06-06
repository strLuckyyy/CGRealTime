import os
import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np

Window       = None
Shader_pista = None
Shader_carro = None
Vao_cubo     = None

WIDTH  = 900
HEIGHT = 650

Tempo_entre_frames = 0.0

Cam_speed = 12.0
Cam_pos   = np.array([0.0, 0.0, 0.0], dtype=np.float32)  # definido no main
Cam_yaw   = 0.0
Cam_pitch = -35.0

lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

fps             = 0
fps_frame_count = 0
fps_accum       = 0.0

NUM_BLOCOS_PISTA = 200
DURACAO_VOLTA    = 7.0


# ── Geração do circuito ───────────────────────────────────────────────────────

def gera_pontos_controle():
    rng    = np.random.default_rng()
    N      = rng.integers(6, 11)
    raio   = rng.uniform(10.0, 16.0)
    angulos = np.linspace(0, 2 * np.pi, N, endpoint=False)
    pts = []
    for a in angulos:
        r = raio + rng.uniform(-raio * 0.45, raio * 0.45)
        pts.append(np.array([np.cos(a) * r, 0.0, np.sin(a) * r], dtype=np.float64))
    return pts


def avalia_catmull_rom(pontos, t_global):
    N     = len(pontos)
    seg_f = t_global * N
    seg_i = int(seg_f) % N
    t     = seg_f - int(seg_f)

    P0 = pontos[(seg_i - 1) % N]
    P1 = pontos[ seg_i]
    P2 = pontos[(seg_i + 1) % N]
    P3 = pontos[(seg_i + 2) % N]

    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2 * P1)
        + (-P0 + P2) * t
        + (2 * P0 - 5 * P1 + 4 * P2 - P3) * t2
        + (-P0 + 3 * P1 - 3 * P2 + P3)    * t3
    )


def discretiza_circuito(pontos, n_amostras=200):
    ts = np.linspace(0, 1, n_amostras, endpoint=False)
    return np.array([avalia_catmull_rom(pontos, t) for t in ts], dtype=np.float32)


# ── Callbacks ────────────────────────────────────────────────────────────────

def redimensiona_callback(window, w, h):
    global WIDTH, HEIGHT
    WIDTH, HEIGHT = w, h


def mouse_callback(window, xpos, ypos):
    global lastX, lastY, primeiro_mouse, Cam_yaw, Cam_pitch
    if primeiro_mouse:
        lastX, lastY = xpos, ypos
        primeiro_mouse = False
    Cam_yaw  += (xpos - lastX) * 0.1
    Cam_pitch = max(-89.0, min(89.0, Cam_pitch + (lastY - ypos) * 0.1))
    lastX, lastY = xpos, ypos


def key_callback(window, key, scancode, action, mode):
    return


# ── OpenGL ───────────────────────────────────────────────────────────────────

def inicializa_opengl():
    global Window
    glfw.init()
    Window = glfw.create_window(WIDTH, HEIGHT, "Circuito Procedural", None, None)
    if not Window:
        glfw.terminate()
        exit()
    glfw.set_window_size_callback(Window, redimensiona_callback)
    glfw.make_context_current(Window)
    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)
    glfw.set_key_callback(Window, key_callback)
    print("GPU:", glGetString(GL_RENDERER))
    print("OpenGL:", glGetString(GL_VERSION))


def inicializa_cubo():
    global Vao_cubo
    Vao_cubo = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo)
    verts = np.array([
        # frontal
         0.5,  0.5,  0.5,   0.5, -0.5,  0.5,  -0.5, -0.5,  0.5,
         0.5,  0.5,  0.5,  -0.5, -0.5,  0.5,  -0.5,  0.5,  0.5,
        # traseira
         0.5,  0.5, -0.5,   0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,
         0.5,  0.5, -0.5,  -0.5, -0.5, -0.5,  -0.5,  0.5, -0.5,
        # esquerda
        -0.5, -0.5,  0.5,  -0.5,  0.5,  0.5,  -0.5, -0.5, -0.5,
        -0.5, -0.5, -0.5,  -0.5,  0.5, -0.5,  -0.5,  0.5,  0.5,
        # direita
         0.5, -0.5,  0.5,   0.5,  0.5,  0.5,   0.5, -0.5, -0.5,
         0.5, -0.5, -0.5,   0.5,  0.5, -0.5,   0.5,  0.5,  0.5,
        # inferior
        -0.5, -0.5,  0.5,   0.5, -0.5,  0.5,   0.5, -0.5, -0.5,
         0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,  -0.5, -0.5,  0.5,
        # superior
        -0.5,  0.5,  0.5,   0.5,  0.5,  0.5,   0.5,  0.5, -0.5,
         0.5,  0.5, -0.5,  -0.5,  0.5, -0.5,  -0.5,  0.5,  0.5,
    ], dtype=np.float32)
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, verts, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)


# ── Shaders ──────────────────────────────────────────────────────────────────

def inicializa_shaders(pontos_curva_gpu):
    global Shader_pista, Shader_carro

    n_pts = len(pontos_curva_gpu)

    vert_pista = f"""
        #version 400
        layout(location = 0) in vec3 vertex_pos;

        uniform int  num_instancias;
        uniform vec3 track_pts[{n_pts}];

        uniform mat4 view;
        uniform mat4 proj;

        void main() {{
            int idx      = gl_InstanceID % {n_pts};
            int idx_prev = (idx - 1 + {n_pts}) % {n_pts};
            int idx_next = (idx + 1) % {n_pts};

            vec3 tang    = normalize(track_pts[idx_next] - track_pts[idx_prev]);
            vec3 up      = vec3(0.0, 1.0, 0.0);
            vec3 right   = normalize(cross(tang, up));
            vec3 real_up = cross(right, tang);

            vec3 scaled  = vertex_pos * vec3(2.5, 0.18, 1.2);
            vec3 rotated = right * scaled.x + real_up * scaled.y + (-tang) * scaled.z;
            vec3 world   = rotated + track_pts[idx] + vec3(0.0, 0.09, 0.0);

            gl_Position = proj * view * vec4(world, 1.0);
        }}
    """

    frag_comum = """
        #version 400
        out vec4 frag_colour;
        uniform vec4 cor_objeto;
        void main() { frag_colour = cor_objeto; }
    """

    vert_carro = """
        #version 400
        layout(location = 0) in vec3 vertex_pos;
        uniform mat4 transform;
        uniform mat4 view;
        uniform mat4 proj;
        void main() {
            gl_Position = proj * view * transform * vec4(vertex_pos, 1.0);
        }
    """

    def compila(vsrc, fsrc):
        vs   = OpenGL.GL.shaders.compileShader(vsrc, GL_VERTEX_SHADER)
        fs   = OpenGL.GL.shaders.compileShader(fsrc, GL_FRAGMENT_SHADER)
        prog = OpenGL.GL.shaders.compileProgram(vs, fs)
        glDeleteShader(vs)
        glDeleteShader(fs)
        return prog

    Shader_pista = compila(vert_pista, frag_comum)
    glUseProgram(Shader_pista)
    for i, pt in enumerate(pontos_curva_gpu):
        glUniform3fv(glGetUniformLocation(Shader_pista, f"track_pts[{i}]"), 1, pt)
    glUniform1i(glGetUniformLocation(Shader_pista, "num_instancias"), NUM_BLOCOS_PISTA)

    Shader_carro = compila(vert_carro, frag_comum)


# ── Câmera ───────────────────────────────────────────────────────────────────

def calcula_frente():
    yr = np.radians(Cam_yaw)
    pr = np.radians(Cam_pitch)
    f  = np.array([
        np.cos(yr) * np.cos(pr),
        np.sin(pr),
        np.sin(yr) * np.cos(pr),
    ], dtype=np.float32)
    return f / np.linalg.norm(f)


def envia_view(shader):
    front = calcula_frente()
    up    = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    s     = np.cross(front, up);  s /= np.linalg.norm(s)
    u     = np.cross(s, front)
    view  = np.identity(4, dtype=np.float32)
    view[0, :3] = s;      view[0, 3] = -np.dot(s,     Cam_pos)
    view[1, :3] = u;      view[1, 3] = -np.dot(u,     Cam_pos)
    view[2, :3] = -front; view[2, 3] =  np.dot(front, Cam_pos)
    glUniformMatrix4fv(glGetUniformLocation(shader, "view"), 1, GL_TRUE, view)


def envia_proj(shader):
    znear, zfar = 0.1, 200.0
    fov = np.radians(67.0)
    asp = WIDTH / HEIGHT
    a = 1 / (np.tan(fov / 2) * asp)
    b = 1 / np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)
    proj = np.array([
        [a, 0, 0, 0], [0, b, 0, 0],
        [0, 0, c, d], [0, 0, -1, 1]
    ], dtype=np.float32)
    glUniformMatrix4fv(glGetUniformLocation(shader, "proj"), 1, GL_TRUE, proj)


# ── Transformações ───────────────────────────────────────────────────────────

def aplica_transform_carro(Tx, Ty, Tz, Sx, Sy, Sz, Ry_deg):
    ry = np.radians(Ry_deg)
    T  = np.array([[1,0,0,Tx],[0,1,0,Ty],[0,0,1,Tz],[0,0,0,1]], dtype=np.float32)
    Ry = np.array([
        [ np.cos(ry), 0, np.sin(ry), 0],
        [0,           1, 0,          0],
        [-np.sin(ry), 0, np.cos(ry), 0],
        [0,           0, 0,          1],
    ], dtype=np.float32)
    S  = np.diag([Sx, Sy, Sz, 1.0]).astype(np.float32)
    glUniformMatrix4fv(
        glGetUniformLocation(Shader_carro, "transform"), 1, GL_TRUE, T @ Ry @ S
    )


def define_cor(shader, r, g, b, a=1.0):
    glUniform4fv(
        glGetUniformLocation(shader, "cor_objeto"), 1,
        np.array([r, g, b, a], dtype=np.float32)
    )


# ── Teclado ──────────────────────────────────────────────────────────────────

def trata_teclado():
    global Cam_pos
    vel    = Cam_speed * Tempo_entre_frames
    frente = calcula_frente()
    dir_   = np.cross(frente, np.array([0.0, 1.0, 0.0], dtype=np.float32))
    dir_  /= np.linalg.norm(dir_)
    if glfw.get_key(Window, glfw.KEY_W) == glfw.PRESS: Cam_pos += frente * vel
    if glfw.get_key(Window, glfw.KEY_S) == glfw.PRESS: Cam_pos -= frente * vel
    if glfw.get_key(Window, glfw.KEY_A) == glfw.PRESS: Cam_pos -= dir_   * vel
    if glfw.get_key(Window, glfw.KEY_D) == glfw.PRESS: Cam_pos += dir_   * vel
    if glfw.get_key(Window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(Window, True)


def build_title():
    return f"Circuito Procedural | FPS: {fps} | WASD: câmera | ESC: sair"


# ── Loop principal ────────────────────────────────────────────────────────────

def loop_renderizacao(pontos_ctrl, curva_pts):
    global Tempo_entre_frames, fps, fps_frame_count, fps_accum

    n_curva        = len(curva_pts)
    tempo_anterior = glfw.get_time()

    glEnable(GL_DEPTH_TEST)

    while not glfw.window_should_close(Window):
        tempo_atual        = glfw.get_time()
        Tempo_entre_frames = tempo_atual - tempo_anterior
        tempo_anterior     = tempo_atual

        fps_frame_count += 1
        fps_accum       += Tempo_entre_frames
        if fps_accum >= 0.5:
            fps             = round(fps_frame_count / fps_accum)
            fps_frame_count = 0
            fps_accum       = 0.0
            glfw.set_window_title(Window, build_title())

        glClearColor(0.08, 0.10, 0.14, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glViewport(0, 0, WIDTH, HEIGHT)

        # Pista
        glUseProgram(Shader_pista)
        envia_view(Shader_pista)
        envia_proj(Shader_pista)
        glBindVertexArray(Vao_cubo)
        define_cor(Shader_pista, 0.22, 0.22, 0.24)
        glUniform1i(glGetUniformLocation(Shader_pista, "num_instancias"), NUM_BLOCOS_PISTA)
        glDrawArraysInstanced(GL_TRIANGLES, 0, 36, NUM_BLOCOS_PISTA)

        glUseProgram(Shader_carro)
        envia_view(Shader_carro)
        envia_proj(Shader_carro)

        # Pontos de controle
        define_cor(Shader_carro, 0.85, 0.15, 0.15)
        for p in pontos_ctrl:
            aplica_transform_carro(p[0], p[1], p[2], 0.4, 0.4, 0.4, 0)
            glDrawArrays(GL_TRIANGLES, 0, 36)

        # Carro animado
        t_global = (tempo_atual % DURACAO_VOLTA) / DURACAO_VOLTA
        idx_f    = t_global * n_curva
        idx_i    = int(idx_f) % n_curva
        idx_n    = (idx_i + 1) % n_curva
        idx_p    = (idx_i - 1) % n_curva
        frac     = idx_f - int(idx_f)

        pos_car = curva_pts[idx_i] * (1 - frac) + curva_pts[idx_n] * frac

        tang  = curva_pts[idx_n] - curva_pts[idx_p]
        norma = np.linalg.norm(tang)
        if norma > 1e-9:
            tang /= norma
        angulo_ry = np.degrees(np.arctan2(tang[0], tang[2]))

        define_cor(Shader_carro, 0.05, 0.75, 0.35)
        aplica_transform_carro(
            pos_car[0], pos_car[1] + 0.55, pos_car[2],
            1.8, 0.6, 3.0,
            angulo_ry
        )
        glDrawArrays(GL_TRIANGLES, 0, 36)

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trata_teclado()

    glfw.terminate()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    global Cam_pos, Cam_yaw, Cam_pitch

    pontos_ctrl = gera_pontos_controle()
    curva_pts   = discretiza_circuito(pontos_ctrl, n_amostras=NUM_BLOCOS_PISTA)

    centro    = curva_pts.mean(axis=0)
    Cam_pos   = np.array([centro[0], centro[1] + 28.0, centro[2] - 5.0], dtype=np.float32)
    Cam_yaw   = 0.0
    Cam_pitch = -70.0

    inicializa_opengl()
    inicializa_cubo()
    inicializa_shaders(curva_pts)
    loop_renderizacao(pontos_ctrl, curva_pts)


if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    main()