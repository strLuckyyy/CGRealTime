# Exemplo 4.1 - Sistema Planetário (Esfera Texturizada + Anel 1D)
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
# - Textura 1D (NOVO): Mapeamento radial para anéis planetários utilizando
#   a distância do centro como coordenada U.
# - Blending (NOVO): Composição alfa para renderizar a transparência da poeira.
#
# DEPENDÊNCIAS:
#   pip install PyOpenGL PyOpenGL_accelerate glfw Pillow numpy

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import ctypes
from PIL import Image

Window                 = None
Shader_programm_esfera = None
Shader_programm_anel   = None
Vao_esfera             = None
Vao_anel               = None
Textura_esfera_id      = None
Textura_anel_id        = None
Num_indices            = 0       
Num_indices_anel       = 0       

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0.0

CAMINHO_TEXTURA_ESFERA = "Aula9\\img\\saturno.jpg"
CAMINHO_TEXTURA_ANEL   = "Aula9\\img\\aneis.png"

# Resolução da malha da esfera:
FATIAS = 64
PILHAS = 32

# -----------------------------
# Parâmetros da câmera virtual
# -----------------------------

Cam_speed  = 3.0
Cam_pos    = np.array([0.0, 1.0, 5.0])
Cam_yaw    = -90.0
Cam_pitch  = -10.0

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
    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo 4.1 - Saturno e Aneis", None, None)
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
# Geração paramétrica da esfera e anel
# -----------------------------------------------

def geraEsfera(raio, fatias, pilhas):
    vertices = []
    indices  = []

    for p in range(pilhas + 1):
        phi = np.pi * p / pilhas
        v   = phi / np.pi

        for f in range(fatias + 1):
            theta = 2.0 * np.pi * f / fatias
            u = f / fatias

            x = raio * np.sin(phi) * np.cos(theta)
            y = raio * np.cos(phi)
            z = raio * np.sin(phi) * np.sin(theta)

            vertices.extend([x, y, z, u, v])

    for p in range(pilhas):
        for f in range(fatias):
            v0 =  p      * (fatias + 1) + f
            v1 =  p      * (fatias + 1) + f + 1
            v2 = (p + 1) * (fatias + 1) + f
            v3 = (p + 1) * (fatias + 1) + f + 1

            indices.extend([v0, v2, v1])
            indices.extend([v1, v2, v3])

    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)

def inicializaEsfera():
    global Vao_esfera, Num_indices

    Vao_esfera = glGenVertexArrays(1)
    glBindVertexArray(Vao_esfera)

    vertices, indices = geraEsfera(raio=1.0, fatias=FATIAS, pilhas=PILHAS)
    Num_indices = len(indices)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    stride = 5 * 4
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

def geraAnel(raio_interno, raio_externo, fatias):
    vertices = []
    indices = []

    for f in range(fatias + 1):
        theta = 2.0 * np.pi * f / fatias
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        
        # Vértice Interno (u = 0.0)
        x_in = raio_interno * cos_t
        z_in = raio_interno * sin_t
        vertices.extend([x_in, 0.0, z_in, 0.0, 0.0]) # v=0.0 apenas para manter o stride
        
        # Vértice Externo (u = 1.0)
        x_out = raio_externo * cos_t
        z_out = raio_externo * sin_t
        vertices.extend([x_out, 0.0, z_out, 1.0, 0.0])
        
    for f in range(fatias):
        v0 = f * 2
        v1 = f * 2 + 1
        v2 = (f + 1) * 2
        v3 = (f + 1) * 2 + 1
        
        indices.extend([v0, v1, v2])
        indices.extend([v2, v1, v3])

    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)

def inicializaAnel():
    global Vao_anel, Num_indices_anel

    Vao_anel = glGenVertexArrays(1)
    glBindVertexArray(Vao_anel)

    # Raios astronômicos aproximados (ex: interno a 1.2x o raio do planeta, externo a 2.3x)
    vertices, indices = geraAnel(raio_interno=1.2, raio_externo=2.3, fatias=FATIAS)
    Num_indices_anel = len(indices)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    stride = 5 * 4
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

# -----------------------------
# Carregamento de textura
# -----------------------------

def carregaTextura2D(caminho):
    global Textura_esfera_id

    img   = Image.open(caminho).convert("RGBA")
    dados = np.array(img, dtype=np.uint8)
    larg, alt = img.size

    Textura_esfera_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, Textura_esfera_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)       
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE) 

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, larg, alt, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, dados)
    glGenerateMipmap(GL_TEXTURE_2D)

def carregaTextura1D(caminho):
    global Textura_anel_id

    img = Image.open(caminho).convert("RGBA")
    dados = np.array(img, dtype=np.uint8)
    larg = img.size[0]

    Textura_anel_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_1D, Textura_anel_id)

    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)

    glTexImage1D(GL_TEXTURE_1D, 0, GL_RGBA, larg, 0, GL_RGBA, GL_UNSIGNED_BYTE, dados)
    glGenerateMipmap(GL_TEXTURE_1D)

# -----------------------------
# Shaders
# -----------------------------

def inicializaShaders():
    global Shader_programm_esfera, Shader_programm_anel

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

    fragment_shader_esfera = """
        #version 400
        in vec2 uv;
        uniform sampler2D textura;

        out vec4 frag_colour;

        void main() {
            frag_colour = texture(textura, uv);
        }
    """

    fragment_shader_anel = """
        #version 400
        in vec2 uv;
        uniform sampler1D textura_anel;

        out vec4 frag_colour;

        void main() {
            frag_colour = texture(textura_anel, uv.x);
            // Descarte simples para otimizar depth-buffer nas áreas invisíveis
            if(frag_colour.a < 0.05) discard;
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    fs_esfera = OpenGL.GL.shaders.compileShader(fragment_shader_esfera, GL_FRAGMENT_SHADER)
    fs_anel = OpenGL.GL.shaders.compileShader(fragment_shader_anel, GL_FRAGMENT_SHADER)

    Shader_programm_esfera = OpenGL.GL.shaders.compileProgram(vs, fs_esfera)
    Shader_programm_anel   = OpenGL.GL.shaders.compileProgram(vs, fs_anel)

    glDeleteShader(vs)
    glDeleteShader(fs_esfera)
    glDeleteShader(fs_anel)

# -----------------------------
# Matrizes
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

def especificaMatrizVisualizacao(shader):
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

    loc = glGetUniformLocation(shader, "view")
    glUniformMatrix4fv(loc, 1, GL_TRUE, view)

def especificaMatrizProjecao(shader):
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

    loc = glGetUniformLocation(shader, "proj")
    glUniformMatrix4fv(loc, 1, GL_TRUE, proj)

def inicializaCamera(shader):
    especificaMatrizVisualizacao(shader)
    especificaMatrizProjecao(shader)

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
    
    # Habilitar Blending para processar a transparência dos anéis
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    while not glfw.window_should_close(Window):
        tempo_atual        = glfw.get_time()
        Tempo_entre_frames = tempo_atual - tempo_anterior
        tempo_anterior     = tempo_atual

        glClearColor(0.02, 0.02, 0.08, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(0, 0, WIDTH, HEIGHT)

        angulo_y = glfw.get_time() * 10.0

        # === 1. Renderiza o Planeta (Esfera) ===
        glUseProgram(Shader_programm_esfera)
        inicializaCamera(Shader_programm_esfera)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, Textura_esfera_id)
        glUniform1i(glGetUniformLocation(Shader_programm_esfera, "textura"), 0)

        glBindVertexArray(Vao_esfera)
        transformacaoGenerica(Shader_programm_esfera, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0, angulo_y, 0)
        glDrawElements(GL_TRIANGLES, Num_indices, GL_UNSIGNED_INT, None)

        # === 2. Renderiza os Anéis ===
        glUseProgram(Shader_programm_anel)
        inicializaCamera(Shader_programm_anel)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_1D, Textura_anel_id)
        glUniform1i(glGetUniformLocation(Shader_programm_anel, "textura_anel"), 0)

        glBindVertexArray(Vao_anel)
        # Aplicamos uma leve inclinação em Z e X para visualização clássica dos anéis
        transformacaoGenerica(Shader_programm_anel, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 20.0, angulo_y, 26.7)
        # Passamos 0.0 para a rotação em Y (Ry), mantendo apenas as inclinações Rx e Rz fixas.
        transformacaoGenerica(Shader_programm_anel, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 20.0, 0.0, 26.7)
        glDrawElements(GL_TRIANGLES, Num_indices_anel, GL_UNSIGNED_INT, None)

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
    inicializaAnel()
    
    inicializaShaders()
    
    # Importante garantir que esses dois arquivos estejam no diretório
    carregaTextura2D(CAMINHO_TEXTURA_ESFERA)
    carregaTextura1D(CAMINHO_TEXTURA_ANEL)
    
    inicializaRenderizacao()

if __name__ == "__main__":
    main()