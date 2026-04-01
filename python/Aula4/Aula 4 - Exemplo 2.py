# Batching e Draw Calls - exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra o impacto de múltiplas draw calls versus batching no desempenho.
#
# Conceitos demonstrados:
# - Draw call: cada chamada glDrawArrays/glDrawElements tem custo de CPU
# - Sem batching: N cubos = N draw calls (gargalo de CPU mesmo com poucos triângulos)
# - Com batching: N cubos = 1 draw call (geometria consolidada em um único VAO)
#
# Controles:
#   W/A/S/D     - mover câmera (FPS)
#   Mouse       - girar câmera
#   B           - alternar entre modo SEM batching e COM batching
#   +/-         - aumentar/diminuir número de cubos na cena
#   ESC         - fechar
#
# HUD no terminal (a cada ~1 segundo):
#   Modo atual, número de cubos, draw calls por frame, FPS médio

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import time

Window = None
Shader_programm = None

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0.0

# -----------------------------
# Parâmetros da câmera virtual
# (idênticos ao exemplo base)
# -----------------------------

Cam_speed     = 10.0
Cam_yaw_speed = 30.0
Cam_pos       = np.array([0.0, 2.0, 12.0])
Cam_yaw       = 180.0   # olhando para a cena
Cam_pitch     = -10.0

lastX, lastY    = WIDTH / 2, HEIGHT / 2
primeiro_mouse  = True

# -----------------------------
# Estado da demonstração
# -----------------------------

# True  → 1 draw call (batching)
# False → N draw calls (sem batching)
Modo_batching = False

# Número de cubos na cena (começa com 500)
Num_cubos = 500

# VAO para o modo sem batching (1 cubo unitário)
Vao_cubo_unitario = None

# VAO para o modo com batching (todos os cubos fundidos)
Vao_batch = None
Batch_vertex_count = 0

# Posições e escalas de cada cubo (geradas uma vez e reutilizadas)
Cubos_transforms = []   # lista de (tx, ty, tz, sx, sy, sz) - rotação fixa em 0

# Acumuladores de FPS para o HUD
_fps_acumulado  = 0
_fps_frames     = 0
_fps_timer      = 0.0

# -----------------------------
# Callbacks de janela e entrada
# -----------------------------

def redimensionaCallback(window, w, h):
    global WIDTH, HEIGHT
    WIDTH  = w
    HEIGHT = h

def mouse_callback(window, xpos, ypos):
    global lastX, lastY, primeiro_mouse, Cam_yaw, Cam_pitch

    if primeiro_mouse:
        lastX, lastY   = xpos, ypos
        primeiro_mouse = False

    xoffset = xpos - lastX
    yoffset = lastY - ypos
    lastX, lastY = xpos, ypos

    sensibilidade = 0.1
    xoffset *= sensibilidade
    yoffset *= sensibilidade

    Cam_yaw   += xoffset
    Cam_pitch += yoffset
    Cam_pitch  = max(-89.0, min(89.0, Cam_pitch))

def key_callback(window, key, scancode, action, mode):
    global Modo_batching, Num_cubos, Vao_batch, Batch_vertex_count

    if action != glfw.PRESS:
        return

    # B - alterna entre os dois modos
    if key == glfw.KEY_B:
        Modo_batching = not Modo_batching
        modo_str = "COM batching (1 draw call)" if Modo_batching else "SEM batching (N draw calls)"
        print(f"\n[MODO] {modo_str}")

    # + / = - mais cubos
    if key in (glfw.KEY_EQUAL, glfw.KEY_KP_ADD):
        Num_cubos = min(Num_cubos + 100, 5000)
        _recria_cubos()
        print(f"[CUBOS] {Num_cubos} cubos na cena")

    # - - menos cubos
    if key in (glfw.KEY_MINUS, glfw.KEY_KP_SUBTRACT):
        Num_cubos = max(Num_cubos - 100, 100)
        _recria_cubos()
        print(f"[CUBOS] {Num_cubos} cubos na cena")

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    glfw.init()

    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo Batching - CG em Tempo Real", None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.set_window_size_callback(Window, redimensionaCallback)
    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)
    glfw.set_key_callback(Window, key_callback)

    print("Placa de vídeo:", glGetString(GL_RENDERER))
    print("Versão do OpenGL:", glGetString(GL_VERSION))

# -----------------------------
# Geometria: vértices de 1 cubo
# -----------------------------
# Retorna array numpy com 36 vértices (xyz) de um cubo unitário centrado na origem.
# Igual ao exemplo base, extraído para reutilização.

def _vertices_cubo():
    points = [
        # face frontal
         0.5,  0.5,  0.5,   0.5, -0.5,  0.5,  -0.5, -0.5,  0.5,
         0.5,  0.5,  0.5,  -0.5, -0.5,  0.5,  -0.5,  0.5,  0.5,
        # face traseira
         0.5,  0.5, -0.5,   0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,
         0.5,  0.5, -0.5,  -0.5, -0.5, -0.5,  -0.5,  0.5, -0.5,
        # face esquerda
        -0.5, -0.5,  0.5,  -0.5,  0.5,  0.5,  -0.5, -0.5, -0.5,
        -0.5, -0.5, -0.5,  -0.5,  0.5, -0.5,  -0.5,  0.5,  0.5,
        # face direita
         0.5, -0.5,  0.5,   0.5,  0.5,  0.5,   0.5, -0.5, -0.5,
         0.5, -0.5, -0.5,   0.5,  0.5, -0.5,   0.5,  0.5,  0.5,
        # face inferior
        -0.5, -0.5,  0.5,   0.5, -0.5,  0.5,   0.5, -0.5, -0.5,
         0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,  -0.5, -0.5,  0.5,
        # face superior
        -0.5,  0.5,  0.5,   0.5,  0.5,  0.5,   0.5,  0.5, -0.5,
         0.5,  0.5, -0.5,  -0.5,  0.5, -0.5,  -0.5,  0.5,  0.5,
    ]
    return np.array(points, dtype=np.float32)

# -----------------------------
# Inicialização: cubo unitário
# -----------------------------
# VAO com 1 cubo - usado no modo SEM batching.
# Cada instância é posicionada via uniform "transform" em um loop de draw calls.

def inicializaCuboUnitario():
    global Vao_cubo_unitario

    Vao_cubo_unitario = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo_unitario)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, _vertices_cubo(), GL_STATIC_DRAW)

    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

# -----------------------------
# Geração dos transforms dos cubos
# -----------------------------
# Distribui N cubos em uma grade com leve variação aleatória de escala.
# Os transforms são fixos durante o exemplo - apenas a contagem muda.

def _gera_transforms(n):
    rng    = np.random.default_rng(42)   # seed fixo: mesma disposição sempre
    lado   = int(np.ceil(np.sqrt(n)))
    result = []

    for i in range(n):
        col = i % lado
        row = i // lado
        tx  = (col - lado / 2.0) * 2.2
        ty  = 0.0
        tz  = (row - lado / 2.0) * 2.2
        s   = float(rng.uniform(0.4, 0.9))
        result.append((tx, ty, tz, s, s, s))

    return result

# -----------------------------
# Construção do batch
# -----------------------------
# Para o modo COM batching, todos os cubos são fundidos em um único VBO.
# Cada vértice já tem sua posição no mundo aplicada (transformação feita na CPU).
# Resultado: 1 VAO, 1 draw call, N * 36 vértices.

def _constroi_batch(transforms):
    cubo_base = _vertices_cubo().reshape(-1, 3)  # (36, 3)
    all_verts = []

    for (tx, ty, tz, sx, sy, sz) in transforms:
        # Aplica escala e translação diretamente nos vértices (sem rotação neste exemplo)
        verts = cubo_base.copy()
        verts[:, 0] = verts[:, 0] * sx + tx
        verts[:, 1] = verts[:, 1] * sy + ty
        verts[:, 2] = verts[:, 2] * sz + tz
        all_verts.append(verts)

    merged = np.concatenate(all_verts, axis=0).astype(np.float32)

    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, merged, GL_STATIC_DRAW)

    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

    return vao, len(merged)

# -----------------------------
# Recria cubos (chamado ao mudar Num_cubos)
# -----------------------------

def _recria_cubos():
    global Cubos_transforms, Vao_batch, Batch_vertex_count

    Cubos_transforms   = _gera_transforms(Num_cubos)
    Vao_batch, Batch_vertex_count = _constroi_batch(Cubos_transforms)

def inicializaCubos():
    inicializaCuboUnitario()
    _recria_cubos()

# -----------------------------
# Shaders
# -----------------------------
# Idênticos ao exemplo base.
# O uniform "transform" é a matriz de modelo de cada cubo.
# No modo com batching, "transform" é sempre a identidade (geometria já está no mundo).

def inicializaShaders():
    global Shader_programm

    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;

        uniform mat4 transform;
        uniform mat4 view;
        uniform mat4 proj;

        void main() {
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
        }
    """

    fragment_shader = """
        #version 400
        out vec4 frag_colour;
        uniform vec4 corobjeto;

        void main() {
            frag_colour = corobjeto;
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    fs = OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    Shader_programm = OpenGL.GL.shaders.compileProgram(vs, fs)

    glDeleteShader(vs)
    glDeleteShader(fs)

# -----------------------------
# Transformação de modelo
# (igual ao exemplo base)
# -----------------------------

def transformacaoGenerica(Tx, Ty, Tz, Sx, Sy, Sz, Rx=0, Ry=0, Rz=0):
    translacao = np.array([
        [1, 0, 0, Tx],
        [0, 1, 0, Ty],
        [0, 0, 1, Tz],
        [0, 0, 0,  1]
    ], dtype=np.float32)

    rx, ry, rz = np.radians([Rx, Ry, Rz])

    rotX = np.array([
        [1,           0,            0, 0],
        [0, np.cos(rx), -np.sin(rx), 0],
        [0, np.sin(rx),  np.cos(rx), 0],
        [0,           0,            0, 1]
    ], dtype=np.float32)

    rotY = np.array([
        [ np.cos(ry), 0, np.sin(ry), 0],
        [          0, 1,          0, 0],
        [-np.sin(ry), 0, np.cos(ry), 0],
        [          0, 0,          0, 1]
    ], dtype=np.float32)

    rotZ = np.array([
        [np.cos(rz), -np.sin(rz), 0, 0],
        [np.sin(rz),  np.cos(rz), 0, 0],
        [         0,           0, 1, 0],
        [         0,           0, 0, 1]
    ], dtype=np.float32)

    escala = np.array([
        [Sx,  0,  0, 0],
        [ 0, Sy,  0, 0],
        [ 0,  0, Sz, 0],
        [ 0,  0,  0, 1]
    ], dtype=np.float32)

    transform = translacao @ rotZ @ rotY @ rotX @ escala

    loc = glGetUniformLocation(Shader_programm, "transform")
    glUniformMatrix4fv(loc, 1, GL_TRUE, transform)

def transformacaoIdentidade():
    """Envia a matriz identidade como transform (usado no modo batching)."""
    identidade = np.identity(4, dtype=np.float32)
    loc = glGetUniformLocation(Shader_programm, "transform")
    glUniformMatrix4fv(loc, 1, GL_TRUE, identidade)

# -----------------------------
# Câmera (matriz de visualização)
# (igual ao exemplo base)
# -----------------------------

def especificaMatrizVisualizacao():
    global Cam_pos, Cam_yaw, Cam_pitch

    front = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    front /= np.linalg.norm(front)

    up = np.array([0.0, 1.0, 0.0])
    s  = np.cross(front, up)
    s /= np.linalg.norm(s)
    u  = np.cross(s, front)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] =  s
    view[1, :3] =  u
    view[2, :3] = -front
    view[0,  3] = -np.dot(s,     Cam_pos)
    view[1,  3] = -np.dot(u,     Cam_pos)
    view[2,  3] =  np.dot(front, Cam_pos)

    loc = glGetUniformLocation(Shader_programm, "view")
    glUniformMatrix4fv(loc, 1, GL_TRUE, view)

# -----------------------------
# Projeção
# (igual ao exemplo base)
# -----------------------------

def especificaMatrizProjecao():
    znear, zfar = 0.1, 200.0
    fov    = np.radians(67.0)
    aspecto = WIDTH / HEIGHT

    a = 1 / (np.tan(fov / 2) * aspecto)
    b = 1 /  np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)

    proj = np.array([
        [a, 0,  0, 0],
        [0, b,  0, 0],
        [0, 0,  c, d],
        [0, 0, -1, 1]
    ], dtype=np.float32)

    loc = glGetUniformLocation(Shader_programm, "proj")
    glUniformMatrix4fv(loc, 1, GL_TRUE, proj)

def inicializaCamera():
    especificaMatrizVisualizacao()
    especificaMatrizProjecao()

# -----------------------------
# Entrada de teclado
# -----------------------------

def trataTeclado():
    global Cam_pos, Tempo_entre_frames

    velocidade = Cam_speed * Tempo_entre_frames

    frente = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    frente /= np.linalg.norm(frente)

    direita = np.cross(frente, np.array([0.0, 1.0, 0.0]))
    direita /= np.linalg.norm(direita)

    if glfw.get_key(Window, glfw.KEY_W) == glfw.PRESS:
        Cam_pos += frente * velocidade
    if glfw.get_key(Window, glfw.KEY_S) == glfw.PRESS:
        Cam_pos -= frente * velocidade
    if glfw.get_key(Window, glfw.KEY_A) == glfw.PRESS:
        Cam_pos -= direita * velocidade
    if glfw.get_key(Window, glfw.KEY_D) == glfw.PRESS:
        Cam_pos += direita * velocidade
    if glfw.get_key(Window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(Window, True)

# -----------------------------
# Definição de cor
# (igual ao exemplo base)
# -----------------------------

def defineCor(r, g, b, a):
    cor = np.array([r, g, b, a], dtype=np.float32)
    loc = glGetUniformLocation(Shader_programm, "corobjeto")
    glUniform4fv(loc, 1, cor)

# -----------------------------
# Renderização sem batching
# -----------------------------
# Cada cubo gera uma draw call independente.
# O custo de CPU cresce linearmente com o número de cubos.

def renderizaSemBatching():
    glBindVertexArray(Vao_cubo_unitario)
    defineCor(0.3, 0.6, 1.0, 1.0)

    for (tx, ty, tz, sx, sy, sz) in Cubos_transforms:
        # Uma draw call por cubo - este é o ponto central da demonstração
        transformacaoGenerica(tx, ty, tz, sx, sy, sz)
        glDrawArrays(GL_TRIANGLES, 0, 36)

    return len(Cubos_transforms)   # número de draw calls

# -----------------------------
# Renderização com batching
# -----------------------------
# Todos os cubos estão fundidos em um único VAO.
# Apenas 1 draw call, independentemente do número de cubos.

def renderizaComBatching():
    glBindVertexArray(Vao_batch)
    defineCor(1.0, 0.6, 0.2, 1.0)

    # Transform identidade: a geometria já está posicionada no mundo
    transformacaoIdentidade()
    glDrawArrays(GL_TRIANGLES, 0, Batch_vertex_count)

    return 1   # número de draw calls

# -----------------------------
# HUD no terminal
# -----------------------------

def atualizaHUD(draw_calls, fps):
    modo_str = "COM batching (1 draw call)" if Modo_batching else "SEM batching (N draw calls)"
    triangulos = Num_cubos * 12   # 12 triângulos por cubo
    print(
        f"\r[{modo_str}]  "
        f"Cubos: {Num_cubos:4d}  |  "
        f"Triângulos: {triangulos:6d}  |  "
        f"Draw calls: {draw_calls:4d}  |  "
        f"FPS: {fps:6.1f}   ",
        end=""
    )

# -----------------------------
# Loop de renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames, _fps_acumulado, _fps_frames, _fps_timer

    tempo_anterior = glfw.get_time()
    _fps_timer     = tempo_anterior

    glEnable(GL_DEPTH_TEST)

    print("\n--- Exemplo: Draw Calls e Batching ---")
    print("  B      - alternar modo (sem / com batching)")
    print("  +/-    - mais/menos cubos na cena")
    print("  W/A/S/D + mouse - câmera FPS")
    print("  ESC    - fechar\n")

    while not glfw.window_should_close(Window):
        tempo_atual          = glfw.get_time()
        Tempo_entre_frames   = tempo_atual - tempo_anterior
        tempo_anterior       = tempo_atual

        # --- Limpa o frame ---
        glClearColor(0.15, 0.15, 0.2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        # --- Renderização no modo escolhido ---
        if Modo_batching:
            draw_calls = renderizaComBatching()
        else:
            draw_calls = renderizaSemBatching()

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

        # --- Acumula FPS para o HUD ---
        _fps_frames     += 1
        _fps_acumulado  += (1.0 / Tempo_entre_frames) if Tempo_entre_frames > 0 else 0.0

        if tempo_atual - _fps_timer >= 1.0:
            fps_medio   = _fps_acumulado / _fps_frames if _fps_frames > 0 else 0.0
            atualizaHUD(draw_calls, fps_medio)
            _fps_acumulado = 0
            _fps_frames    = 0
            _fps_timer     = tempo_atual

    glfw.terminate()

# -----------------------------
# Função principal
# -----------------------------

def main():
    inicializaOpenGL()
    inicializaShaders()
    inicializaCubos()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()