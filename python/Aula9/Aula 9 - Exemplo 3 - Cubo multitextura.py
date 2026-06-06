# Exemplo 3 - Cubo Multi-Textura (bloco de grama do Minecraft)
# Disciplina de Computação Gráfica em Tempo Real
#
# CONCEITOS INTRODUZIDOS NESTE EXEMPLO:
# - Múltiplas texturas: carregar e gerenciar mais de uma textura na GPU.
# - Unidades de textura (Texture Units): o OpenGL suporta várias texturas
#   ativas simultaneamente (GL_TEXTURE0, GL_TEXTURE1, GL_TEXTURE2...).
#   Cada unidade recebe um ID de textura e um sampler2D no shader.
# - Atributo de "ID de face" por vértice: um terceiro atributo inteiro (float
#   usado como int) passado ao shader para identificar qual face está sendo
#   desenhada, permitindo selecionar a textura correta.
# - Lógica de seleção de textura no fragment shader: usando if/else ou
#   um array de samplers para escolher qual textura amostrar por fragmento.
#
# TEXTURAS NECESSÁRIAS (3 arquivos):
#   grass_top.png  - textura do topo (grama verde)
#   grass_side.png - textura das laterais (grama + terra)
#   dirt.png       - textura do fundo (terra pura)
#
#   Todas disponíveis em qualquer resource pack do Minecraft, ou busque
#   "minecraft grass block texture png" no Google Imagens.
#   Tamanho original: 16x16 pixels — funciona perfeitamente com GL_NEAREST.
#
# CONTROLES:
#   W/A/S/D - movimenta a câmera
#   Mouse   - rotaciona a câmera (yaw + pitch)
#   ESC     - fecha a janela
#
# DEPENDÊNCIAS:
#   pip install PyOpenGL PyOpenGL_accelerate glfw Pillow

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import ctypes
from PIL import Image

Window          = None
Shader_programm = None
Vao_cubo        = None

# Armazenamos os 3 IDs de textura em uma lista para facilitar o acesso
# Índice 0 = topo | Índice 1 = lateral | Índice 2 = fundo
Texturas        = [None, None, None]

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0.0

CAMINHO_TOPO    = "Aula9\\img\\grass_top.jpg"
CAMINHO_LATERAL = "Aula9\\img\\grass_side.jpg"
CAMINHO_FUNDO   = "Aula9\\img\\dirt.jpg"

# -----------------------------
# Parâmetros da câmera virtual
# -----------------------------

Cam_speed     = 5.0
Cam_pos       = np.array([0.0, 0.5, 3.0])
Cam_yaw       = 0.0
Cam_pitch     = -10.0   # leve ângulo para baixo para ver o topo do bloco

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
    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo 3 - Cubo Multi-Textura (Grama)", None, None)
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
# NOVIDADE: cada vértice agora carrega um terceiro atributo — o ID da face.
# Formato por vértice: (x, y, z,  u, v,  face_id)
#
# IDs de face definidos:
#   0.0 = face SUPERIOR  → textura do topo (grama)
#   1.0 = faces LATERAIS → textura da lateral (grama+terra)
#   2.0 = face INFERIOR  → textura do fundo (terra)
#
# O fragment shader recebe esse valor e decide qual sampler2D usar.
# Usamos float em vez de int para compatibilidade com glVertexAttribPointer.

def inicializaCubo():
    global Vao_cubo

    Vao_cubo = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo)

    # Formato: x, y, z,  u, v,  face_id
    vertices = np.array([

        # --- Face FRONTAL (lateral) — face_id = 1.0 ---
        -0.5, -0.5,  0.5,   0.0, 0.0,   1.0,
         0.5, -0.5,  0.5,   1.0, 0.0,   1.0,
         0.5,  0.5,  0.5,   1.0, 1.0,   1.0,
        -0.5, -0.5,  0.5,   0.0, 0.0,   1.0,
         0.5,  0.5,  0.5,   1.0, 1.0,   1.0,
        -0.5,  0.5,  0.5,   0.0, 1.0,   1.0,

        # --- Face TRASEIRA (lateral) — face_id = 1.0 ---
         0.5, -0.5, -0.5,   0.0, 0.0,   1.0,
        -0.5, -0.5, -0.5,   1.0, 0.0,   1.0,
        -0.5,  0.5, -0.5,   1.0, 1.0,   1.0,
         0.5, -0.5, -0.5,   0.0, 0.0,   1.0,
        -0.5,  0.5, -0.5,   1.0, 1.0,   1.0,
         0.5,  0.5, -0.5,   0.0, 1.0,   1.0,

        # --- Face ESQUERDA (lateral) — face_id = 1.0 ---
        -0.5, -0.5, -0.5,   0.0, 0.0,   1.0,
        -0.5, -0.5,  0.5,   1.0, 0.0,   1.0,
        -0.5,  0.5,  0.5,   1.0, 1.0,   1.0,
        -0.5, -0.5, -0.5,   0.0, 0.0,   1.0,
        -0.5,  0.5,  0.5,   1.0, 1.0,   1.0,
        -0.5,  0.5, -0.5,   0.0, 1.0,   1.0,

        # --- Face DIREITA (lateral) — face_id = 1.0 ---
         0.5, -0.5,  0.5,   0.0, 0.0,   1.0,
         0.5, -0.5, -0.5,   1.0, 0.0,   1.0,
         0.5,  0.5, -0.5,   1.0, 1.0,   1.0,
         0.5, -0.5,  0.5,   0.0, 0.0,   1.0,
         0.5,  0.5, -0.5,   1.0, 1.0,   1.0,
         0.5,  0.5,  0.5,   0.0, 1.0,   1.0,

        # --- Face INFERIOR (fundo) — face_id = 2.0 ---
        -0.5, -0.5, -0.5,   0.0, 0.0,   2.0,
         0.5, -0.5, -0.5,   1.0, 0.0,   2.0,
         0.5, -0.5,  0.5,   1.0, 1.0,   2.0,
        -0.5, -0.5, -0.5,   0.0, 0.0,   2.0,
         0.5, -0.5,  0.5,   1.0, 1.0,   2.0,
        -0.5, -0.5,  0.5,   0.0, 1.0,   2.0,

        # --- Face SUPERIOR (topo) — face_id = 0.0 ---
        -0.5,  0.5,  0.5,   0.0, 0.0,   0.0,
         0.5,  0.5,  0.5,   1.0, 0.0,   0.0,
         0.5,  0.5, -0.5,   1.0, 1.0,   0.0,
        -0.5,  0.5,  0.5,   0.0, 0.0,   0.0,
         0.5,  0.5, -0.5,   1.0, 1.0,   0.0,
        -0.5,  0.5, -0.5,   0.0, 1.0,   0.0,

    ], dtype=np.float32)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Stride: 6 floats por vértice = 24 bytes
    stride = 6 * 4

    # Atributo 0: posição (x, y, z) — offset 0
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)

    # Atributo 1: UV (u, v) — offset de 3 floats = 12 bytes
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

    # Atributo 2: face_id (1 float) — offset de 5 floats = 20 bytes
    glEnableVertexAttribArray(2)
    glVertexAttribPointer(2, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(5 * 4))

# -----------------------------------------------
# Carregamento de múltiplas texturas
# -----------------------------------------------
# Cada textura recebe um ID próprio da GPU (glGenTextures).
# No momento do draw, vinculamos cada ID a uma unidade de textura diferente:
#   GL_TEXTURE0 ← textura do topo    → sampler2D tex_topo    (unit 0)
#   GL_TEXTURE1 ← textura lateral    → sampler2D tex_lateral (unit 1)
#   GL_TEXTURE2 ← textura do fundo   → sampler2D tex_fundo   (unit 2)

def carregaTextura(caminho):
    """Carrega uma imagem e envia para a GPU. Retorna o ID de textura gerado."""
    img   = Image.open(caminho).convert("RGBA")
    img   = img.transpose(Image.FLIP_TOP_BOTTOM)
    dados = np.array(img, dtype=np.uint8)
    larg, alt = img.size

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, larg, alt, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, dados)
    glGenerateMipmap(GL_TEXTURE_2D)

    print(f"Textura carregada: {caminho} ({larg}x{alt}) → ID {tex_id}")
    return tex_id

def carregaTodasTexturas():
    global Texturas
    Texturas[0] = carregaTextura(CAMINHO_TOPO)
    Texturas[1] = carregaTextura(CAMINHO_LATERAL)
    Texturas[2] = carregaTextura(CAMINHO_FUNDO)

# -----------------------------
# Shaders
# -----------------------------
# NOVIDADE no fragment shader:
# - Três samplers (tex_topo, tex_lateral, tex_fundo) correspondendo às 3 unidades.
# - A variável 'face_id' chega interpolada do vertex shader.
#   Como todos os vértices de uma face têm o mesmo face_id, não há interpolação
#   real — o valor chega idêntico em todos os fragmentos daquela face.
# - Um if/else seleciona qual sampler usar com base no face_id arredondado.

def inicializaShaders():
    global Shader_programm

    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        layout(location = 1) in vec2 tex_coord;
        layout(location = 2) in float face_id_in;   // qual face é esta?

        uniform mat4 transform;
        uniform mat4 view;
        uniform mat4 proj;

        out vec2 uv;
        out float face_id;   // repassado ao fragment shader

        void main() {
            uv      = tex_coord;
            face_id = face_id_in;
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
        }
    """

    fragment_shader = """
        #version 400
        in vec2  uv;
        in float face_id;

        // Uma unidade de textura por tipo de face
        uniform sampler2D tex_topo;      // unidade 0
        uniform sampler2D tex_lateral;   // unidade 1
        uniform sampler2D tex_fundo;     // unidade 2

        out vec4 frag_colour;

        void main() {
            // Arredonda face_id para evitar imprecisões de float
            int fid = int(round(face_id));

            if (fid == 0) {
                frag_colour = texture(tex_topo, uv);
            } else if (fid == 1) {
                frag_colour = texture(tex_lateral, uv);
            } else {
                frag_colour = texture(tex_fundo, uv);
            }
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    fs = OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    Shader_programm = OpenGL.GL.shaders.compileProgram(vs, fs)

    glDeleteShader(vs)
    glDeleteShader(fs)

# -----------------------------------------------
# Vincula as texturas às unidades antes do draw
# -----------------------------------------------
# Esta função deve ser chamada a cada frame, dentro do loop de renderização.
# Ela associa cada ID de textura à sua unidade e aponta os uniforms do shader.

def ativaTexturas():
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, Texturas[0])
    glUniform1i(glGetUniformLocation(Shader_programm, "tex_topo"), 0)

    glActiveTexture(GL_TEXTURE1)
    glBindTexture(GL_TEXTURE_2D, Texturas[1])
    glUniform1i(glGetUniformLocation(Shader_programm, "tex_lateral"), 1)

    glActiveTexture(GL_TEXTURE2)
    glBindTexture(GL_TEXTURE_2D, Texturas[2])
    glUniform1i(glGetUniformLocation(Shader_programm, "tex_fundo"), 2)

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

        glClearColor(0.4, 0.7, 1.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        # Vincula as 3 texturas às suas respectivas unidades
        ativaTexturas()

        glBindVertexArray(Vao_cubo)

        # Pequeno grid de blocos de grama para demonstrar o efeito
        for linha in range(3):
            for coluna in range(3):
                tx = (coluna - 1) * 1.2
                tz = (linha  - 1) * 1.2
                transformacaoGenerica(tx, 0.0, tz,  1.0, 1.0, 1.0,  0, 0, 0)
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
    carregaTodasTexturas()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()
