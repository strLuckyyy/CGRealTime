# Exemplo 5 - Skybox com Cubemap
# Disciplina de Computação Gráfica em Tempo Real
#
# CONCEITOS INTRODUZIDOS NESTE EXEMPLO:
# - GL_TEXTURE_CUBE_MAP: tipo especial de textura formado por 6 faces
#   (direita, esquerda, topo, base, frente, trás), cada uma sendo uma
#   imagem quadrada independente.
# - Coordenadas de textura 3D (vec3): em vez de UV (2D), o cubemap é
#   amostrado com um vetor de direção 3D — o próprio vértice do cubo
#   serve como direção, sem precisar de UVs explícitas.
# - Skybox trick: o cubo é desenhado sem translação (apenas rotação da
#   câmera é aplicada), e com o depth test configurado para GL_LEQUAL,
#   garantindo que o skybox sempre fique "atrás" de tudo.
# - Remoção da translação da view matrix: zeramos a coluna de translação
#   da matriz de visualização antes de passá-la ao shader do skybox, para
#   que o cubo acompanhe a câmera sem se afastar dela.
#
# TEXTURAS NECESSÁRIAS (6 arquivos, todos quadrados e do mesmo tamanho):
#   right.png, left.png, top.png, bottom.png, front.png, back.png
#
#   Onde encontrar:
#   - LearnOpenGL skybox clássico:
#     https://learnopengl.com/img/textures/skybox.zip
#   - OpenGameArt: https://opengameart.org  (busque "skybox")
#   - Humus: http://www.humus.name/index.php?page=Textures
#
#   Coloque os 6 arquivos na mesma pasta do script (ou ajuste PASTA_SKYBOX).
#
# CONTROLES:
#   W/A/S/D - movimenta a câmera (o skybox acompanha — é o comportamento correto)
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
import os
from PIL import Image

Window              = None
Shader_skybox       = None   # shader exclusivo do skybox (sem transform, sem UV)
Shader_objeto       = None   # shader normal para objetos da cena
Vao_skybox          = None
Vao_cubo            = None
Textura_cubemap     = None
Textura_cubo        = None   # textura simples para o cubo de exemplo na cena

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0.0

# Pasta onde estão os 6 arquivos de textura do skybox
PASTA_SKYBOX    = "Aula9\\skybox"
TEXTURA_OBJETO  = "Aula9\\img\\dirt.jpg"   # qualquer textura para o cubo de referência na cena

# -----------------------------
# Parâmetros da câmera virtual
# -----------------------------

Cam_speed  = 5.0
Cam_pos    = np.array([0.0, 0.0, 3.0])
Cam_yaw    = 0.0
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
    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo 5 - Skybox com Cubemap", None, None)
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
# Geometria do skybox
# -----------------------------------------------
# O skybox é um cubo simples centrado na origem, com lado 1.
# NÃO usamos UVs aqui — as coordenadas de textura do cubemap são
# derivadas diretamente da posição do vértice (vec3), que serve como
# vetor de direção apontando para a face correta do cubemap.
#
# A ordem dos vértices segue a convenção do OpenGL para cubemaps:
# cada face é vista de dentro do cubo, então a ordem dos triângulos
# é invertida em relação ao cubo normal (face culling invertido).

def inicializaSkybox():
    global Vao_skybox

    Vao_skybox = glGenVertexArrays(1)
    glBindVertexArray(Vao_skybox)

    # Apenas posições (x, y, z) — sem UV, sem face_id
    # A posição do vértice É a direção de amostragem do cubemap
    vertices = np.array([
        # face DIREITA  (+X)
         1.0, -1.0, -1.0,
         1.0, -1.0,  1.0,
         1.0,  1.0,  1.0,
         1.0,  1.0,  1.0,
         1.0,  1.0, -1.0,
         1.0, -1.0, -1.0,
        # face ESQUERDA (-X)
        -1.0, -1.0,  1.0,
        -1.0, -1.0, -1.0,
        -1.0,  1.0, -1.0,
        -1.0,  1.0, -1.0,
        -1.0,  1.0,  1.0,
        -1.0, -1.0,  1.0,
        # face TOPO     (+Y)
        -1.0,  1.0, -1.0,
         1.0,  1.0, -1.0,
         1.0,  1.0,  1.0,
         1.0,  1.0,  1.0,
        -1.0,  1.0,  1.0,
        -1.0,  1.0, -1.0,
        # face BASE     (-Y)
        -1.0, -1.0, -1.0,
        -1.0, -1.0,  1.0,
         1.0, -1.0, -1.0,
         1.0, -1.0, -1.0,
        -1.0, -1.0,  1.0,
         1.0, -1.0,  1.0,
        # face FRENTE   (+Z)
        -1.0, -1.0,  1.0,
        -1.0,  1.0,  1.0,
         1.0,  1.0,  1.0,
         1.0,  1.0,  1.0,
         1.0, -1.0,  1.0,
        -1.0, -1.0,  1.0,
        # face TRÁS     (-Z)
        -1.0,  1.0, -1.0,
         1.0,  1.0, -1.0,
         1.0, -1.0, -1.0,
         1.0, -1.0, -1.0,
        -1.0, -1.0, -1.0,
        -1.0,  1.0, -1.0,
    ], dtype=np.float32)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Apenas atributo 0: posição (x, y, z)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * 4, None)

# -----------------------------------------------
# Geometria do cubo de referência na cena
# -----------------------------------------------
# Um cubo normal texturizado para dar referência espacial ao skybox.
# Sem ele, é difícil perceber que a câmera está se movendo.

def inicializaCubo():
    global Vao_cubo

    Vao_cubo = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo)

    vertices = np.array([
        -0.5, -0.5,  0.5,   0.0, 0.0,
         0.5, -0.5,  0.5,   1.0, 0.0,
         0.5,  0.5,  0.5,   1.0, 1.0,
        -0.5, -0.5,  0.5,   0.0, 0.0,
         0.5,  0.5,  0.5,   1.0, 1.0,
        -0.5,  0.5,  0.5,   0.0, 1.0,
         0.5, -0.5, -0.5,   0.0, 0.0,
        -0.5, -0.5, -0.5,   1.0, 0.0,
        -0.5,  0.5, -0.5,   1.0, 1.0,
         0.5, -0.5, -0.5,   0.0, 0.0,
        -0.5,  0.5, -0.5,   1.0, 1.0,
         0.5,  0.5, -0.5,   0.0, 1.0,
        -0.5, -0.5, -0.5,   0.0, 0.0,
        -0.5, -0.5,  0.5,   1.0, 0.0,
        -0.5,  0.5,  0.5,   1.0, 1.0,
        -0.5, -0.5, -0.5,   0.0, 0.0,
        -0.5,  0.5,  0.5,   1.0, 1.0,
        -0.5,  0.5, -0.5,   0.0, 1.0,
         0.5, -0.5,  0.5,   0.0, 0.0,
         0.5, -0.5, -0.5,   1.0, 0.0,
         0.5,  0.5, -0.5,   1.0, 1.0,
         0.5, -0.5,  0.5,   0.0, 0.0,
         0.5,  0.5, -0.5,   1.0, 1.0,
         0.5,  0.5,  0.5,   0.0, 1.0,
        -0.5, -0.5, -0.5,   0.0, 0.0,
         0.5, -0.5, -0.5,   1.0, 0.0,
         0.5, -0.5,  0.5,   1.0, 1.0,
        -0.5, -0.5, -0.5,   0.0, 0.0,
         0.5, -0.5,  0.5,   1.0, 1.0,
        -0.5, -0.5,  0.5,   0.0, 1.0,
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

    stride = 5 * 4
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

# -----------------------------------------------
# Carregamento do Cubemap
# -----------------------------------------------
# Um cubemap é carregado face a face, cada uma com um target diferente:
#
#   GL_TEXTURE_CUBE_MAP_POSITIVE_X → right.png   (face direita)
#   GL_TEXTURE_CUBE_MAP_NEGATIVE_X → left.png    (face esquerda)
#   GL_TEXTURE_CUBE_MAP_POSITIVE_Y → top.png     (face superior)
#   GL_TEXTURE_CUBE_MAP_NEGATIVE_Y → bottom.png  (face inferior)
#   GL_TEXTURE_CUBE_MAP_POSITIVE_Z → front.png   (face frontal)
#   GL_TEXTURE_CUBE_MAP_NEGATIVE_Z → back.png    (face traseira)
#
# IMPORTANTE: faces do cubemap NÃO devem ser flipadas verticalmente.
# O sistema de coordenadas do cubemap já usa Y para cima nativamente.

def carregaCubemap(pasta):
    global Textura_cubemap

    faces = [
        ("right.jpg",  GL_TEXTURE_CUBE_MAP_POSITIVE_X),
        ("left.jpg",   GL_TEXTURE_CUBE_MAP_NEGATIVE_X),
        ("top.jpg",    GL_TEXTURE_CUBE_MAP_POSITIVE_Y),
        ("bottom.jpg", GL_TEXTURE_CUBE_MAP_NEGATIVE_Y),
        ("front.jpg",  GL_TEXTURE_CUBE_MAP_POSITIVE_Z),
        ("back.jpg",   GL_TEXTURE_CUBE_MAP_NEGATIVE_Z),
    ]

    Textura_cubemap = glGenTextures(1)
    glBindTexture(GL_TEXTURE_CUBE_MAP, Textura_cubemap)

    for nome, target in faces:
        caminho = os.path.join(pasta, nome)
        img     = Image.open(caminho).convert("RGB")   # cubemap usa RGB (sem alpha)
        
        # NÃO flipar — cubemap já tem Y para cima
        dados   = np.array(img, dtype=np.uint8)
        larg, alt = img.size

        glTexImage2D(target, 0, GL_RGB, larg, alt, 0,
                     GL_RGB, GL_UNSIGNED_BYTE, dados)
        print(f"  Face carregada: {nome} ({larg}x{alt})")

    # GL_LINEAR para suavidade nas bordas entre faces
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # GL_CLAMP_TO_EDGE em todos os 3 eixos: evita costuras visíveis
    # nas bordas onde duas faces do cubemap se encontram
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)

    print(f"Cubemap carregado: {pasta}/")

def carregaTexturaSimples(caminho):
    global Textura_cubo

    img   = Image.open(caminho).convert("RGBA")
    img   = img.transpose(Image.FLIP_TOP_BOTTOM)
    dados = np.array(img, dtype=np.uint8)
    larg, alt = img.size

    Textura_cubo = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, Textura_cubo)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, larg, alt, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, dados)
    glGenerateMipmap(GL_TEXTURE_2D)
    print(f"Textura do objeto carregada: {caminho}")

# -----------------------------------------------
# Shaders
# -----------------------------------------------
# Dois programas de shader distintos:
#
# 1) Shader do SKYBOX:
#    - Vertex: recebe só posição (vec3). Constrói a view SEM translação
#      (coluna 3 zerada) para o cubo sempre rodear a câmera.
#      gl_Position.z = gl_Position.w força o fragmento ao valor máximo
#      de profundidade (z=1 após divisão perspectiva), garantindo que
#      o skybox fique atrás de tudo com GL_LEQUAL.
#    - Fragment: usa samplerCube (não sampler2D), amostrado com vec3.
#
# 2) Shader do OBJETO:
#    - Pipeline normal com transform + view + proj + sampler2D.

def inicializaShaders():
    global Shader_skybox, Shader_objeto

    # --- Shader do Skybox ---
    vs_skybox = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;

        uniform mat4 view;
        uniform mat4 proj;

        out vec3 dir_textura;   // direção de amostragem para o samplerCube

        void main() {
            dir_textura = vertex_posicao;   // posição do vértice = direção no espaço

            // View sem translação: apenas a parte 3x3 superior (rotação)
            // Isso é feito na CPU antes de passar a uniform (veja especificaViewSkybox)
            vec4 pos = proj * view * vec4(vertex_posicao, 1.0);

            // Força z = w → após divisão perspectiva z/w = 1.0 (profundidade máxima)
            // Combinado com GL_LEQUAL, o skybox passa no depth test mas fica atrás
            gl_Position = pos.xyww;
        }
    """

    fs_skybox = """
        #version 400
        in vec3 dir_textura;
        uniform samplerCube skybox;   // cubemap — amostrado com vec3

        out vec4 frag_colour;

        void main() {
            frag_colour = texture(skybox, dir_textura);
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vs_skybox, GL_VERTEX_SHADER)
    fs = OpenGL.GL.shaders.compileShader(fs_skybox, GL_FRAGMENT_SHADER)
    Shader_skybox = OpenGL.GL.shaders.compileProgram(vs, fs)
    glDeleteShader(vs)
    glDeleteShader(fs)

    # --- Shader do Objeto ---
    vs_objeto = """
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

    fs_objeto = """
        #version 400
        in vec2 uv;
        uniform sampler2D textura;

        out vec4 frag_colour;

        void main() {
            frag_colour = texture(textura, uv);
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vs_objeto, GL_VERTEX_SHADER)
    fs = OpenGL.GL.shaders.compileShader(fs_objeto, GL_FRAGMENT_SHADER)
    Shader_objeto = OpenGL.GL.shaders.compileProgram(vs, fs)
    glDeleteShader(vs)
    glDeleteShader(fs)

# -----------------------------
# Câmera — duas versões da view
# -----------------------------

def calculaFront():
    front = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    return front / np.linalg.norm(front)

def montaViewMatrix(front, remover_translacao=False):
    """
    Monta a matriz de visualização.
    Se remover_translacao=True, zera a coluna de translação —
    usado pelo skybox para que ele acompanhe a câmera sem se deslocar.
    """
    up = np.array([0.0, 1.0, 0.0])
    s  = np.cross(front, up);  s /= np.linalg.norm(s)
    u  = np.cross(s, front)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] =  s
    view[1, :3] =  u
    view[2, :3] = -front

    if not remover_translacao:
        view[0, 3] = -np.dot(s,     Cam_pos)
        view[1, 3] = -np.dot(u,     Cam_pos)
        view[2, 3] =  np.dot(front, Cam_pos)
    # se remover_translacao=True, coluna 3 permanece zero → só rotação

    return view

def montaProjecaoMatrix():
    znear, zfar = 0.1, 100.0
    fov     = np.radians(67.0)
    aspecto = WIDTH / HEIGHT

    a = 1 / (np.tan(fov / 2) * aspecto)
    b = 1 /  np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)

    return np.array([
        [a, 0,  0, 0],
        [0, b,  0, 0],
        [0, 0,  c, d],
        [0, 0, -1, 0]
    ], dtype=np.float32)

# -----------------------------
# Transformação de modelo
# -----------------------------

def transformacaoGenerica(shader, Tx, Ty, Tz, Sx, Sy, Sz, Rx, Ry, Rz):
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
    loc = glGetUniformLocation(shader, "transform")
    glUniformMatrix4fv(loc, 1, GL_TRUE, transform)

# -----------------------------
# Teclado
# -----------------------------

def trataTeclado():
    global Cam_pos

    velocidade = Cam_speed * Tempo_entre_frames
    frente  = calculaFront()
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

# -----------------------------------------------
# Renderização
# -----------------------------------------------
# ORDEM DE DRAW — crítica para o skybox funcionar:
#
#   1) Desenha os objetos normais primeiro (com depth test normal GL_LESS)
#   2) Muda depth test para GL_LEQUAL
#   3) Desenha o skybox (gl_Position.xyww força z=1 → sempre no fundo)
#   4) Restaura GL_LESS para o próximo frame
#
# Por que GL_LEQUAL e não GL_LESS?
#   O skybox tem profundidade z=1.0 (máxima). O depth buffer é inicializado
#   com 1.0. Com GL_LESS, z=1.0 não passaria (1.0 < 1.0 é falso).
#   Com GL_LEQUAL, 1.0 <= 1.0 é verdadeiro → o skybox é desenhado apenas
#   onde nenhum objeto foi renderizado.

def inicializaRenderizacao():
    global Tempo_entre_frames

    tempo_anterior = glfw.get_time()
    glEnable(GL_DEPTH_TEST)

    proj = montaProjecaoMatrix()
    
    # ATIVA A FILTRAGEM SEM COSTURAS ENTRE AS FACES DO CUBEMAP
    glEnable(GL_TEXTURE_CUBE_MAP_SEAMLESS)
    
    while not glfw.window_should_close(Window):
        tempo_atual        = glfw.get_time()
        Tempo_entre_frames = tempo_atual - tempo_anterior
        tempo_anterior     = tempo_atual

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glViewport(0, 0, WIDTH, HEIGHT)

        front = calculaFront()

        # ---- 1) Objetos normais da cena ----
        view_normal = montaViewMatrix(front, remover_translacao=False)

        glDepthFunc(GL_LESS)
        glUseProgram(Shader_objeto)

        glUniformMatrix4fv(glGetUniformLocation(Shader_objeto, "view"), 1, GL_TRUE, view_normal)
        glUniformMatrix4fv(glGetUniformLocation(Shader_objeto, "proj"), 1, GL_TRUE, proj)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, Textura_cubo)
        glUniform1i(glGetUniformLocation(Shader_objeto, "textura"), 0)

        glBindVertexArray(Vao_cubo)

        # Alguns cubos espalhados na cena como referência espacial
        posicoes = [
            ( 0.0,  0.0,  0.0),
            ( 2.5,  0.0, -1.0),
            (-2.0,  0.5,  1.5),
            ( 1.0, -1.0,  2.0),
        ]
        for tx, ty, tz in posicoes:
            transformacaoGenerica(Shader_objeto, tx, ty, tz, 1, 1, 1, 0, 0, 0)
            glDrawArrays(GL_TRIANGLES, 0, 36)

        # ---- 2) Skybox — sempre por último ----
        # View sem translação: câmera gira mas o skybox não se afasta
        view_skybox = montaViewMatrix(front, remover_translacao=True)

        glDepthFunc(GL_LEQUAL)   # deixa z=1.0 passar no depth test
        glUseProgram(Shader_skybox)

        glUniformMatrix4fv(glGetUniformLocation(Shader_skybox, "view"), 1, GL_TRUE, view_skybox)
        glUniformMatrix4fv(glGetUniformLocation(Shader_skybox, "proj"), 1, GL_TRUE, proj)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_CUBE_MAP, Textura_cubemap)
        glUniform1i(glGetUniformLocation(Shader_skybox, "skybox"), 0)

        glBindVertexArray(Vao_skybox)
        glDrawArrays(GL_TRIANGLES, 0, 36)

        # Restaura para o próximo frame
        glDepthFunc(GL_LESS)

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

    glfw.terminate()

# -----------------------------
# Função principal
# -----------------------------

def main():
    inicializaOpenGL()
    inicializaSkybox()
    inicializaCubo()
    inicializaShaders()
    carregaCubemap(PASTA_SKYBOX)
    carregaTexturaSimples(TEXTURA_OBJETO)
    inicializaRenderizacao()

if __name__ == "__main__":
    main()
