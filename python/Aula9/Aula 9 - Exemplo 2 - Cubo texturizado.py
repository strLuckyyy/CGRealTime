# Exemplo 2 - Cubo Texturizado (estilo bloco do Minecraft)
# Disciplina de Computação Gráfica em Tempo Real
#
# CONCEITOS INTRODUZIDOS NESTE EXEMPLO:
# - Coordenadas UV por face: cada face do cubo tem suas próprias UVs,
#   mapeando a textura completa do (0,0) ao (1,1) em cada face.
# - VBO interleaved com câmera FPS: posição + UV no mesmo buffer,
#   combinado com a câmera yaw+pitch do exemplo base.
# - Depth test: necessário para o cubo aparecer corretamente em 3D.
# - Uma textura aplicada igualmente em todas as 6 faces (como blocos do Minecraft).
#
# TEXTURA SUGERIDA:
#   Baixe a textura de terra/pedra do Minecraft (dirt.png, stone.png, etc.)
#   de qualquer resource pack ou busque "minecraft dirt texture png" no Google.
#   Coloque na mesma pasta e ajuste CAMINHO_TEXTURA.
#   A textura original é 16x16 — funciona perfeitamente, o GL_NEAREST
#   preserva o visual pixelado característico.
#
# CONTROLES:
#   W/A/S/D    - movimenta a câmera
#   Mouse      - rotaciona a câmera (yaw + pitch)
#   ESC        - fecha a janela
#
# DEPENDÊNCIAS:
#   pip install PyOpenGL PyOpenGL_accelerate glfw Pillow

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import ctypes
from PIL import Image

Window         = None
Shader_programm = None
Vao_cubo       = None
Textura_id     = None

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0.0

CAMINHO_TEXTURA = "Aula9\\img\\dirt.jpg"   # troque pelo nome da sua textura

# -----------------------------
# Parâmetros da câmera virtual
# -----------------------------

Cam_speed     = 5.0
Cam_pos       = np.array([0.0, 0.0, 3.0])
Cam_yaw       = -90.0
Cam_pitch     = 0.0

lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# -----------------------------
# Callbacks
# -----------------------------

def redimensionaCallback(window, w, h):
    global WIDTH, HEIGHT
    WIDTH, HEIGHT = w, h

def mouse_callback(window, xpos, ypos):
    global lastX, lastY, primeiro_mouse, Cam_yaw, Cam_pitch

    if primeiro_mouse:
        lastX, lastY   = xpos, ypos
        primeiro_mouse = False

    xoffset = (xpos - lastX) * 0.1
    yoffset = (lastY - ypos) * 0.1
    lastX, lastY = xpos, ypos

    Cam_yaw   += xoffset
    Cam_pitch  = max(-89.0, min(89.0, Cam_pitch + yoffset))

def key_callback(window, key, scancode, action, mode):
    return

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    glfw.init()
    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo 2 - Cubo Texturizado (Minecraft)", None, None)
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

# -----------------------------------------------
# Inicialização da geometria
# -----------------------------------------------
# Cada face do cubo é formada por 2 triângulos (6 vértices por face).
# Cada vértice carrega: posição (x,y,z) + UV (u,v)
#
# As UVs vão de (0,0) a (1,1) em CADA face individualmente,
# fazendo a textura aparecer completa em todas as 6 faces — exatamente
# como o Minecraft faz com seus blocos.
#
# Diagrama de uma face com suas UVs:
#
#   v1(0,1)----v2(1,1)
#      |  tri1  /|
#      |      /  |
#      |    /    |
#      |  /  tri2|
#   v0(0,0)----v3(1,0)
#
#   tri1 = v1, v0, v3   |   tri2 = v1, v3, v2

def inicializaCubo():
    global Vao_cubo

    Vao_cubo = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo)

    # Cada bloco de 5 valores: (x, y, z, u, v)
    # Organizado face a face para facilitar a leitura
    vertices = np.array([

        # --- Face FRONTAL (z = +0.5) ---
        # normal aponta para +Z
        -0.5, -0.5,  0.5,   0.0, 0.0,
         0.5, -0.5,  0.5,   1.0, 0.0,
         0.5,  0.5,  0.5,   1.0, 1.0,
        -0.5, -0.5,  0.5,   0.0, 0.0,
         0.5,  0.5,  0.5,   1.0, 1.0,
        -0.5,  0.5,  0.5,   0.0, 1.0,

        # --- Face TRASEIRA (z = -0.5) ---
        # vértices em ordem invertida para a normal apontar para -Z
         0.5, -0.5, -0.5,   0.0, 0.0,
        -0.5, -0.5, -0.5,   1.0, 0.0,
        -0.5,  0.5, -0.5,   1.0, 1.0,
         0.5, -0.5, -0.5,   0.0, 0.0,
        -0.5,  0.5, -0.5,   1.0, 1.0,
         0.5,  0.5, -0.5,   0.0, 1.0,

        # --- Face ESQUERDA (x = -0.5) ---
        -0.5, -0.5, -0.5,   0.0, 0.0,
        -0.5, -0.5,  0.5,   1.0, 0.0,
        -0.5,  0.5,  0.5,   1.0, 1.0,
        -0.5, -0.5, -0.5,   0.0, 0.0,
        -0.5,  0.5,  0.5,   1.0, 1.0,
        -0.5,  0.5, -0.5,   0.0, 1.0,

        # --- Face DIREITA (x = +0.5) ---
         0.5, -0.5,  0.5,   0.0, 0.0,
         0.5, -0.5, -0.5,   1.0, 0.0,
         0.5,  0.5, -0.5,   1.0, 1.0,
         0.5, -0.5,  0.5,   0.0, 0.0,
         0.5,  0.5, -0.5,   1.0, 1.0,
         0.5,  0.5,  0.5,   0.0, 1.0,

        # --- Face INFERIOR (y = -0.5) ---
        -0.5, -0.5, -0.5,   0.0, 0.0,
         0.5, -0.5, -0.5,   1.0, 0.0,
         0.5, -0.5,  0.5,   1.0, 1.0,
        -0.5, -0.5, -0.5,   0.0, 0.0,
         0.5, -0.5,  0.5,   1.0, 1.0,
        -0.5, -0.5,  0.5,   0.0, 1.0,

        # --- Face SUPERIOR (y = +0.5) ---
        -0.5,  0.5,  0.5,   0.0, 0.0,
         0.5,  0.5,  0.5,   1.0, 0.0,
         0.5,  0.5, -0.5,   1.0, 1.0,
        -0.5,  0.5,  0.5,   0.0, 0.0,
         0.5,  0.5, -0.5,   1.0, 1.0,
        -0.5,  0.5, -0.5,   0.0, 1.0,

    ], dtype=np.float32)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Stride: 5 floats por vértice = 20 bytes
    stride = 5 * 4

    # Atributo 0: posição (x, y, z) — offset 0
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)

    # Atributo 1: UV (u, v) — offset de 3 floats = 12 bytes
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

# -----------------------------------------------
# Carregamento de textura
# -----------------------------------------------
# GL_NEAREST é usado aqui intencionalmente:
# preserva o visual pixelado das texturas 16x16 do Minecraft.
# Troque por GL_LINEAR se quiser suavização.

def carregaTextura(caminho):
    global Textura_id

    img    = Image.open(caminho).convert("RGBA")
    img    = img.transpose(Image.FLIP_TOP_BOTTOM)
    dados  = np.array(img, dtype=np.uint8)
    larg, alt = img.size

    Textura_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, Textura_id)

    # GL_NEAREST_MIPMAP_NEAREST: pixel mais próximo ao reduzir (distância)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_NEAREST)
    # GL_NEAREST: pixel mais próximo ao ampliar — mantém o visual pixelado
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, larg, alt, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, dados)
    glGenerateMipmap(GL_TEXTURE_2D)

    print(f"Textura carregada: {caminho} ({larg}x{alt})")

# -----------------------------
# Shaders
# -----------------------------

def inicializaShaders():
    global Shader_programm

    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        layout(location = 1) in vec2 tex_coord;

        uniform mat4 transform;
        uniform mat4 view;
        uniform mat4 proj;

        out vec2 uv;

        void main() {
            uv = tex_coord;
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
        }
    """

    fragment_shader = """
        #version 400
        in vec2 uv;
        uniform sampler2D textura;

        out vec4 frag_colour;

        void main() {
            frag_colour = texture(textura, uv);
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    fs = OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    Shader_programm = OpenGL.GL.shaders.compileProgram(vs, fs)

    glDeleteShader(vs)
    glDeleteShader(fs)

# -----------------------------
# Transformação de modelo
# -----------------------------

def transformacaoGenerica(Tx, Ty, Tz, Sx, Sy, Sz, Rx, Ry, Rz):
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
# -----------------------------

def especificaMatrizVisualizacao():
    front = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    front /= np.linalg.norm(front)

    up = np.array([0.0, 1.0, 0.0])
    s  = np.cross(front, up);  s /= np.linalg.norm(s)
    u  = np.cross(s, front)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] =  s;    view[0, 3] = -np.dot(s,     Cam_pos)
    view[1, :3] =  u;    view[1, 3] = -np.dot(u,     Cam_pos)
    view[2, :3] = -front; view[2, 3] =  np.dot(front, Cam_pos)

    loc = glGetUniformLocation(Shader_programm, "view")
    glUniformMatrix4fv(loc, 1, GL_TRUE, view)

# -----------------------------
# Projeção
# -----------------------------

def especificaMatrizProjecao():
    znear, zfar = 0.1, 100.0
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
        [0, 0, -1, 0]
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
    global Cam_pos

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
        Cam_pos += frente  * velocidade
    if glfw.get_key(Window, glfw.KEY_S) == glfw.PRESS:
        Cam_pos -= frente  * velocidade
    if glfw.get_key(Window, glfw.KEY_A) == glfw.PRESS:
        Cam_pos -= direita * velocidade
    if glfw.get_key(Window, glfw.KEY_D) == glfw.PRESS:
        Cam_pos += direita * velocidade
    if glfw.get_key(Window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(Window, True)

# -----------------------------
# Renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames

    tempo_anterior = glfw.get_time()

    glEnable(GL_DEPTH_TEST)

    while not glfw.window_should_close(Window):
        tempo_atual        = glfw.get_time()
        Tempo_entre_frames = tempo_atual - tempo_anterior
        tempo_anterior     = tempo_atual

        glClearColor(0.4, 0.7, 1.0, 1.0)   # céu azul de fundo
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        # Ativa a textura na unidade 0
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, Textura_id)
        glUniform1i(glGetUniformLocation(Shader_programm, "textura"), 0)

        glBindVertexArray(Vao_cubo)

        # Desenha um grid de blocos 3x3 para demonstrar instâncias do mesmo cubo
        for linha in range(3):
            for coluna in range(3):
                tx = (coluna - 1) * 1.2    # espaço de 1.2 entre blocos
                ty = 0.0
                tz = (linha  - 1) * 1.2
                transformacaoGenerica(tx, ty, tz,  1.0, 1.0, 1.0,  0, 0, 0)
                glDrawArrays(GL_TRIANGLES, 0, 36)

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

    glfw.terminate()

# -----------------------------
# Função principal
# -----------------------------

def main():
    inicializaOpenGL()
    inicializaCubo()
    inicializaShaders()
    carregaTextura(CAMINHO_TEXTURA)
    inicializaRenderizacao()

if __name__ == "__main__":
    main()
