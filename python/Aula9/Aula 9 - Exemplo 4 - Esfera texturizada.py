# Exemplo 4 - Esfera Texturizada (Geração Paramétrica)
# Disciplina de Computação Gráfica em Tempo Real
#
# CONCEITOS INTRODUZIDOS NESTE EXEMPLO:
# - Geração paramétrica de esfera: vértices calculados via senos e cossenos
#   a partir de dois ângulos (phi = latitude, theta = longitude).
# - UVs naturais da parametrização: theta e phi mapeiam diretamente para
#   U e V, resultando em mapeamento equiretangular sem nenhum cálculo extra.
# - EBO (Element Buffer Object) com índices: a malha da esfera é definida
#   por uma grade de vértices únicos + índices que formam os triângulos,
#   evitando duplicação de vértices (muito mais eficiente que lista plana).
# - Textura equiretangular: imagem 2:1 (largura = 2x altura) que representa
#   a superfície esférica planificada — como um mapa-múndi.
#
# TEXTURA SUGERIDA:
#   Qualquer imagem equiretangular (proporção 2:1). Exemplos:
#   - Textura da Terra: https://visibleearth.nasa.gov  (busque "Blue Marble")
#   - Planetas prontos: https://www.solarsystemscope.com/textures/
#   - Busca: "earth texture map equirectangular png"
#   Salve como "planeta.png" na mesma pasta (ou ajuste CAMINHO_TEXTURA).
#
# CONTROLES:
#   W/A/S/D - movimenta a câmera
#   Mouse   - rotaciona a câmera (yaw + pitch)
#   ESC     - fecha a janela
#
# DEPENDÊNCIAS:
#   pip install PyOpenGL PyOpenGL_accelerate glfw Pillow numpy

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import ctypes
from PIL import Image

Window          = None
Shader_programm = None
Vao_esfera      = None
Textura_id      = None
Num_indices     = 0       # quantidade de índices gerados (varia com a resolução)

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0.0

CAMINHO_TEXTURA = "Aula9\\img\\earth.jpg"

# Resolução da malha da esfera:
# Fatias (slices) = divisões ao redor do eixo Y (longitude) — como meridianos
# Pilhas (stacks) = divisões ao longo do eixo Y (latitude)  — como paralelos
# Quanto maior, mais suave a esfera. 32x32 já é bem suave.
FATIAS = 64
PILHAS = 32

# -----------------------------
# Parâmetros da câmera virtual
# -----------------------------

Cam_speed  = 3.0
Cam_pos    = np.array([0.0, 0.0, 3.0])
Cam_yaw    = -90.0
Cam_pitch  = 0.0

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
    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo 4 - Esfera Texturizada", None, None)
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
# Geração paramétrica da esfera
# -----------------------------------------------
# A parametrização usa dois ângulos:
#
#   phi   (φ): ângulo de LATITUDE — varia de 0 (polo norte) a π (polo sul)
#   theta (θ): ângulo de LONGITUDE — varia de 0 a 2π (volta completa)
#
# Equações paramétricas (raio = 1):
#   x = sin(φ) * cos(θ)
#   y = cos(φ)
#   z = sin(φ) * sin(θ)
#
# UVs derivadas diretamente dos ângulos normalizados:
#   u = θ / (2π)   → varia de 0 (esquerda) a 1 (direita)  — longitude
#   v = φ / π      → varia de 0 (topo)     a 1 (base)     — latitude
#
# Isso gera um mapeamento equiretangular: a textura 2:1 se encaixa
# perfeitamente, com o polo norte no topo e o polo sul na base.
#
# Estrutura da malha (grid de vértices):
#
#   pilha 0 (polo norte): 1 anel de (FATIAS+1) vértices
#   pilha 1 ..PILHAS-1  : anéis intermediários
#   pilha PILHAS (polo sul): último anel
#
#   Cada célula da grade → 2 triângulos → indexados no EBO
#
#   Grade vista de cima (u × v):
#
#   v0---v1---v2--- ...
#   |  \ |  \ |
#   |   \|   \|
#   v_n--...
#
# Total de vértices: (FATIAS+1) * (PILHAS+1)
# Total de índices : FATIAS * PILHAS * 6  (2 triângulos × 3 vértices)

def geraEsfera(raio, fatias, pilhas):
    vertices = []   # lista de (x, y, z, u, v)
    indices  = []   # lista de índices inteiros

    for p in range(pilhas + 1):
        phi = np.pi * p / pilhas          # 0 .. π

        v   = phi / np.pi                 # UV vertical: 0 (topo) .. 1 (base)

        for f in range(fatias + 1):
            theta = 2.0 * np.pi * f / fatias   # 0 .. 2π

            u = f / fatias                      # UV horizontal: 0 .. 1

            x = raio * np.sin(phi) * np.cos(theta)
            y = raio * np.cos(phi)
            z = raio * np.sin(phi) * np.sin(theta)

            vertices.extend([x, y, z, u, v])

    # Geração dos índices
    # Para cada célula (pilha p, fatia f), criamos 2 triângulos:
    #
    #   v0 ---- v1
    #   |  tri1/ |
    #   |    /   |
    #   |  / tri2|
    #   v2 ---- v3
    #
    #   v0 = p     * (fatias+1) + f
    #   v1 = p     * (fatias+1) + f + 1
    #   v2 = (p+1) * (fatias+1) + f
    #   v3 = (p+1) * (fatias+1) + f + 1

    for p in range(pilhas):
        for f in range(fatias):
            v0 =  p      * (fatias + 1) + f
            v1 =  p      * (fatias + 1) + f + 1
            v2 = (p + 1) * (fatias + 1) + f
            v3 = (p + 1) * (fatias + 1) + f + 1

            # Triângulo 1: v0, v2, v1
            indices.extend([v0, v2, v1])
            # Triângulo 2: v1, v2, v3
            indices.extend([v1, v2, v3])

    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)

def inicializaEsfera():
    global Vao_esfera, Num_indices

    Vao_esfera = glGenVertexArrays(1)
    glBindVertexArray(Vao_esfera)

    vertices, indices = geraEsfera(raio=1.0, fatias=FATIAS, pilhas=PILHAS)
    Num_indices = len(indices)

    print(f"Esfera gerada: {len(vertices)//5} vértices, {Num_indices//3} triângulos")

    # VBO: envia os vértices (x, y, z, u, v)
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # EBO: envia os índices
    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    # Stride: 5 floats por vértice = 20 bytes
    stride = 5 * 4

    # Atributo 0: posição (x, y, z) — offset 0
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)

    # Atributo 1: UV (u, v) — offset de 3 floats = 12 bytes
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

# -----------------------------
# Carregamento de textura
# -----------------------------

def carregaTextura(caminho):
    global Textura_id

    img   = Image.open(caminho).convert("RGBA")
    #img   = img.transpose(Image.FLIP_TOP_BOTTOM)
    dados = np.array(img, dtype=np.uint8)
    larg, alt = img.size

    Textura_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, Textura_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # GL_CLAMP_TO_EDGE nos polos evita artefatos nas bordas da textura
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)       # horizontal: repete
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE) # vertical: prende nas bordas

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
# Câmera
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
    view[0, :3] =  s;     view[0, 3] = -np.dot(s,     Cam_pos)
    view[1, :3] =  u;     view[1, 3] = -np.dot(u,     Cam_pos)
    view[2, :3] = -front; view[2, 3] =  np.dot(front, Cam_pos)

    loc = glGetUniformLocation(Shader_programm, "view")
    glUniformMatrix4fv(loc, 1, GL_TRUE, view)

def especificaMatrizProjecao():
    znear, zfar = 0.1, 100.0
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
        [0, 0, -1, 0]
    ], dtype=np.float32)

    loc = glGetUniformLocation(Shader_programm, "proj")
    glUniformMatrix4fv(loc, 1, GL_TRUE, proj)

def inicializaCamera():
    especificaMatrizVisualizacao()
    especificaMatrizProjecao()

# -----------------------------
# Teclado
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

        glClearColor(0.02, 0.02, 0.08, 1.0)   # fundo escuro estilo espaço
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, Textura_id)
        glUniform1i(glGetUniformLocation(Shader_programm, "textura"), 0)

        glBindVertexArray(Vao_esfera)

        # Rotação lenta ao longo do eixo Y — simula rotação do planeta
        angulo_y = glfw.get_time() * 10.0   # 10 graus por segundo

        transformacaoGenerica(0.0, 0.0, 0.0,  1.0, 1.0, 1.0,  0, angulo_y, 0)

        # glDrawElements usa o EBO para percorrer os índices e montar os triângulos
        glDrawElements(GL_TRIANGLES, Num_indices, GL_UNSIGNED_INT, None)

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

    glfw.terminate()

# -----------------------------
# Função principal
# -----------------------------

def main():
    inicializaOpenGL()
    inicializaEsfera()
    inicializaShaders()
    carregaTextura(CAMINHO_TEXTURA)
    inicializaRenderizacao()

if __name__ == "__main__":
    main()
