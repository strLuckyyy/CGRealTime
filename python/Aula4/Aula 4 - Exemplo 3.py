# LOD Dinâmico com Distância - exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra Level of Detail (LOD): usar versões diferentes da mesma
# malha conforme a distância da câmera, equilibrando qualidade visual e desempenho.
#
# Conceitos demonstrados:
# - LOD discreto: troca abrupta entre versões da malha
# - Microtriângulos distantes não contribuem para a silhueta percebida
# - O número de triângulos ativos na cena varia com a posição da câmera
# - Gargalo geométrico: mais triângulos → mais execuções do vertex shader
#
# A cena contém N esferas aproximadas (icoesferas) distribuídas em grade.
# Cada esfera tem 4 versões de malha:
#   LOD 0 (muito perto) - altíssima resolução (~20480 triângulos)
#   LOD 1 (perto)       - alta resolução      (~5120 triângulos)
#   LOD 2 (médio)       - média resolução     (~1280 triângulos)
#   LOD 3 (longe)       - baixa resolução     (~80 triângulos)
#
# Controles:
#   W/A/S/D     - mover câmera (FPS)
#   Mouse       - girar câmera
#   L           - alternar LOD automático ON/OFF (força LOD 0 quando OFF)
#   F           - alternar wireframe
#   ESC         - fechar
#
# HUD no terminal (a cada ~1 segundo):
#   LOD automático, triângulos ativos, distribuição LOD0/1/2, FPS médio

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np

Window        = None
Shader_programm = None

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0.0

# -----------------------------
# Parâmetros da câmera virtual
# (idênticos ao exemplo base)
# -----------------------------

Cam_speed  = 15.0
Cam_pos    = np.array([0.0, 2.0, 20.0])
Cam_yaw    = -90.0
Cam_pitch  = -10.0

lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# -----------------------------
# Estado da demonstração
# -----------------------------

# True  → troca de LOD automática por distância
# False → força LOD 0 (alta resolução) em todos os objetos
LOD_automatico = True

# Exibe wireframe para visualizar a malha ativa
Wireframe = False

# Limiares de distância para troca de LOD
# Objetos com dist < LIMIAR_0 usam LOD 0, etc.
LIMIAR_LOD_0 = 15.0
LIMIAR_LOD_1 = 40.0
LIMIAR_LOD_2 = 80.0
# dist >= LIMIAR_LOD_2 → LOD 3 (mais baixo)

# VAOs das 4 versões da esfera (LOD 0..3)
# Cada entrada: (vao, vertex_count)
Vaos_esferas = [None, None, None, None]

# Posições das esferas na cena
Esferas_pos = []

# Número de esferas na cena
NUM_ESFERAS = 900   # grade 30x30  ← aumentado para forçar gargalo geométrico

# Acumuladores para o HUD
_fps_acumulado = 0
_fps_frames    = 0
_fps_timer     = 0.0

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

    xoffset =  xpos - lastX
    yoffset =  lastY - ypos
    lastX, lastY = xpos, ypos

    sensibilidade = 0.1
    Cam_yaw   += xoffset * sensibilidade
    Cam_pitch += yoffset * sensibilidade
    Cam_pitch  = max(-89.0, min(89.0, Cam_pitch))

def key_callback(window, key, scancode, action, mode):
    global LOD_automatico, Wireframe

    if action != glfw.PRESS:
        return

    if key == glfw.KEY_L:
        LOD_automatico = not LOD_automatico
        estado = "AUTOMÁTICO" if LOD_automatico else "FORÇADO LOD 0 (alta resolução)"
        print(f"\n[LOD] {estado}")

    if key == glfw.KEY_F:
        Wireframe = not Wireframe
        if Wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        estado = "ON" if Wireframe else "OFF"
        print(f"\n[WIREFRAME] {estado}")

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    glfw.init()

    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo LOD - CG em Tempo Real", None, None)
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
# Geração de icosfera
# -----------------------------
# Uma icosfera é uma esfera construída por subdivisão de um icosaedro.
# Cada nível de subdivisão multiplica os triângulos por 4.
#
# subdivisoes=0 →   20 triângulos  (icosaedro puro)
# subdivisoes=1 →   80 triângulos  (LOD 2 - longe)
# subdivisoes=2 →  320 triângulos  (LOD 1 - médio)
# subdivisoes=3 → 1280 triângulos  (LOD 0 - perto)
#
# Retorna array numpy float32 com os vértices (xyz) prontos para GL_TRIANGLES.

def _gera_icosfera(subdivisoes=2, raio=0.8):
    # --- Vértices iniciais do icosaedro ---
    t = (1.0 + np.sqrt(5.0)) / 2.0

    verts_base = np.array([
        [-1,  t,  0], [ 1,  t,  0], [-1, -t,  0], [ 1, -t,  0],
        [ 0, -1,  t], [ 0,  1,  t], [ 0, -1, -t], [ 0,  1, -t],
        [ t,  0, -1], [ t,  0,  1], [-t,  0, -1], [-t,  0,  1],
    ], dtype=np.float64)

    # Normaliza para ficar na superfície da esfera unitária
    verts_base /= np.linalg.norm(verts_base[0])

    faces = [
        (0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),
        (1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
        (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),
        (4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1),
    ]

    # Cache de pontos médios para evitar duplicatas
    cache_meio = {}

    def ponto_medio(v, a, b):
        chave = (min(a, b), max(a, b))
        if chave in cache_meio:
            return cache_meio[chave]
        meio = (v[a] + v[b]) / 2.0
        meio /= np.linalg.norm(meio)
        v.append(meio)
        idx = len(v) - 1
        cache_meio[chave] = idx
        return idx

    verts = list(verts_base)

    for _ in range(subdivisoes):
        novas_faces = []
        for (a, b, c) in faces:
            ab = ponto_medio(verts, a, b)
            bc = ponto_medio(verts, b, c)
            ca = ponto_medio(verts, c, a)
            novas_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = novas_faces
        cache_meio.clear()

    # Monta array de vértices para GL_TRIANGLES (sem índices)
    verts_np = np.array(verts, dtype=np.float64) * raio
    triangulos = []
    for (a, b, c) in faces:
        triangulos.extend([verts_np[a], verts_np[b], verts_np[c]])

    return np.array(triangulos, dtype=np.float32).flatten()

# -----------------------------
# Inicialização das esferas (3 LODs)
# -----------------------------

def _cria_vao_esfera(subdivisoes):
    verts = _gera_icosfera(subdivisoes)

    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, verts, GL_STATIC_DRAW)

    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

    vertex_count = len(verts) // 3
    return vao, vertex_count

def inicializaEsferas():
    global Vaos_esferas, Esferas_pos

    # LOD 0 - altíssima resolução (muito perto)  ~20480 triângulos
    vao0, vc0 = _cria_vao_esfera(subdivisoes=5)
    # LOD 1 - alta resolução (perto)             ~5120 triângulos
    vao1, vc1 = _cria_vao_esfera(subdivisoes=4)
    # LOD 2 - média resolução                    ~1280 triângulos
    vao2, vc2 = _cria_vao_esfera(subdivisoes=3)
    # LOD 3 - baixa resolução (longe)            ~80 triângulos
    vao3, vc3 = _cria_vao_esfera(subdivisoes=1)

    Vaos_esferas = [(vao0, vc0), (vao1, vc1), (vao2, vc2), (vao3, vc3)]

    print(f"  LOD 0 (muito perto): {vc0 // 3:6d} triângulos")
    print(f"  LOD 1 (perto):       {vc1 // 3:6d} triângulos")
    print(f"  LOD 2 (médio):       {vc2 // 3:6d} triângulos")
    print(f"  LOD 3 (longe):       {vc3 // 3:6d} triângulos\n")

    # Distribui esferas em grade (lado x lado) com espaçamento maior
    lado = int(np.ceil(np.sqrt(NUM_ESFERAS)))
    for i in range(NUM_ESFERAS):
        col = i % lado
        row = i // lado
        tx  = (col - lado / 2.0) * 6.0
        tz  = (row - lado / 2.0) * 6.0
        Esferas_pos.append(np.array([tx, 0.0, tz]))

# -----------------------------
# Shaders
# (idênticos ao exemplo base)
# -----------------------------

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

def transformacaoGenerica(Tx, Ty, Tz, Sx=1, Sy=1, Sz=1, Rx=0, Ry=0, Rz=0):
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

# -----------------------------
# Câmera (matriz de visualização)
# (igual ao exemplo base)
# -----------------------------

def especificaMatrizVisualizacao():
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
    znear, zfar = 0.1, 300.0
    fov     = np.radians(67.0)
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
# Cor de cada LOD
# -----------------------------
# Cores distintas ajudam o aluno a identificar visualmente qual LOD está ativo
# em cada esfera durante a navegação da cena.
#
#   LOD 0 - azul   (alta resolução, perto)
#   LOD 1 - verde  (média resolução)
#   LOD 2 - laranja (baixa resolução, longe)

CORES_LOD = [
    (0.2, 0.5, 1.0, 1.0),   # LOD 0 - azul     (muito perto, ~20480 tri)
    (0.3, 0.9, 0.4, 1.0),   # LOD 1 - verde     (perto,       ~5120 tri)
    (1.0, 0.9, 0.2, 1.0),   # LOD 2 - amarelo   (médio,       ~1280 tri)
    (1.0, 0.4, 0.1, 1.0),   # LOD 3 - laranja   (longe,         ~80 tri)
]

def defineCor(r, g, b, a):
    cor = np.array([r, g, b, a], dtype=np.float32)
    loc = glGetUniformLocation(Shader_programm, "corobjeto")
    glUniform4fv(loc, 1, cor)

# -----------------------------
# Seleção de LOD por distância
# -----------------------------
# Função central do exemplo: dado um objeto, retorna qual LOD usar
# com base na distância euclidiana até a câmera.
#
# Esta é a lógica de LOD discreto descrita na aula:
# troca abrupta entre níveis conforme a distância.

def selecionaLOD(pos_objeto):
    dist = float(np.linalg.norm(Cam_pos - pos_objeto))
    if dist < LIMIAR_LOD_0:
        return 0
    elif dist < LIMIAR_LOD_1:
        return 1
    elif dist < LIMIAR_LOD_2:
        return 2
    else:
        return 3

# -----------------------------
# Renderização
# -----------------------------

def renderizaCena():
    contagem_lod = [0, 0, 0, 0]
    total_triangulos = 0

    for pos in Esferas_pos:
        if LOD_automatico:
            lod = selecionaLOD(pos)
        else:
            lod = 0

        vao, vertex_count = Vaos_esferas[lod]
        r, g, b, a = CORES_LOD[lod]

        glBindVertexArray(vao)
        defineCor(r, g, b, a)
        transformacaoGenerica(pos[0], pos[1], pos[2])
        glDrawArrays(GL_TRIANGLES, 0, vertex_count)

        contagem_lod[lod] += 1
        total_triangulos   += vertex_count // 3

    return total_triangulos, contagem_lod

# -----------------------------
# HUD no terminal
# -----------------------------

def atualizaHUD(total_tri, contagem_lod, fps):
    modo_str = "AUTOMÁTICO" if LOD_automatico else "FORÇADO LOD 0"
    wire_str = " [WIREFRAME]" if Wireframe else ""
    print(
        f"\r[LOD {modo_str}]{wire_str}  "
        f"Triângulos: {total_tri:8d}  |  "
        f"LOD0(azul): {contagem_lod[0]:3d}  "
        f"LOD1(verde): {contagem_lod[1]:3d}  "
        f"LOD2(amarelo): {contagem_lod[2]:3d}  "
        f"LOD3(laranja): {contagem_lod[3]:3d}  |  "
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

    print("\n--- Exemplo: LOD Dinâmico por Distância ---")
    print("  W/A/S/D + mouse - câmera FPS (aproxime e afaste das esferas)")
    print("  L               - alternar LOD automático ON/OFF")
    print("  F               - alternar wireframe (veja a malha ativa)")
    print("  ESC             - fechar")
    print(f"\n  Limiares de distância: LOD0 < {LIMIAR_LOD_0}  |  LOD1 < {LIMIAR_LOD_1}  |  LOD2 < {LIMIAR_LOD_2}  |  LOD3 >= {LIMIAR_LOD_2}")
    print(f"  Cores: LOD0=azul (muito perto)  LOD1=verde  LOD2=amarelo  LOD3=laranja (longe)\n")

    while not glfw.window_should_close(Window):
        tempo_atual        = glfw.get_time()
        Tempo_entre_frames = tempo_atual - tempo_anterior
        tempo_anterior     = tempo_atual

        glClearColor(0.12, 0.12, 0.18, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        total_tri, contagem_lod = renderizaCena()

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

        # Acumula FPS para o HUD
        _fps_frames    += 1
        _fps_acumulado += (1.0 / Tempo_entre_frames) if Tempo_entre_frames > 0 else 0.0

        if tempo_atual - _fps_timer >= 1.0:
            fps_medio      = _fps_acumulado / _fps_frames if _fps_frames > 0 else 0.0
            atualizaHUD(total_tri, contagem_lod, fps_medio)
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
    inicializaEsferas()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()