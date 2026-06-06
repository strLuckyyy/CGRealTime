# Exemplo 1 - Quad Texturizado
# Disciplina de Computação Gráfica em Tempo Real
#
# CONCEITOS INTRODUZIDOS NESTE EXEMPLO:
# - Coordenadas de textura (UV): cada vértice recebe um par (u, v) que mapeia
#   a posição do vértice na imagem. (0,0) é canto inferior esquerdo, (1,1) é canto superior direito.
# - VBO interleaved: posição e UV juntos no mesmo buffer, intercalados por vértice.
# - glVertexAttribPointer com stride e offset: como o OpenGL "lê" atributos intercalados.
# - Carregamento de textura com Pillow: abre a imagem, converte para RGBA, envia para a GPU.
# - Sampler2D no fragment shader: como o shader acessa a textura usando as coordenadas UV.
#
# DEPENDÊNCIAS:
#   pip install PyOpenGL PyOpenGL_accelerate glfw Pillow
#
# TEXTURA:
#   Coloque qualquer imagem .png ou .jpg na mesma pasta e informe o nome em CAMINHO_TEXTURA.
#   Sugestões: uma foto, um emoji salvo como PNG, qualquer imagem simples.

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
from PIL import Image

Window = None
Shader_programm = None
Vao_quad = None
Textura_id = None

WIDTH  = 800
HEIGHT = 600

# -------------------------------------------------------
# Altere aqui para o nome/caminho da sua imagem de textura
# -------------------------------------------------------
CAMINHO_TEXTURA = "Aula9\\img\\tiles.jpg"

# -----------------------------
# Callbacks de janela e entrada
# -----------------------------

def redimensionaCallback(window, w, h):
    global WIDTH, HEIGHT
    WIDTH  = w
    HEIGHT = h

def key_callback(window, key, scancode, action, mode):
    if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
        glfw.set_window_should_close(window, True)

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    glfw.init()

    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo 1 - Quad Texturizado", None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.set_window_size_callback(Window, redimensionaCallback)
    glfw.set_key_callback(Window, key_callback)
    glfw.make_context_current(Window)

    print("Placa de vídeo:", glGetString(GL_RENDERER))
    print("Versão do OpenGL:", glGetString(GL_VERSION))

# -----------------------------------------------
# Inicialização da geometria
# -----------------------------------------------
# Um quad é formado por 2 triângulos que juntos formam um retângulo.
#
# Cada linha abaixo representa um vértice com 5 valores:
#   (x, y, z,   u, v)
#    ^^^^^^^^^^^  ^^^^
#    posição 3D   coordenada de textura (UV)
#
# Visualizando o quad e suas UVs:
#
#   (-0.5, 0.5)────────(0.5, 0.5)      UV: (0,1)──────(1,1)
#       │      \  tri2  │                    │    \      │
#       │  tri1  \      │                    │      \    │
#   (-0.5,-0.5)───(0.5,-0.5)           UV: (0,0)──────(1,0)
#
# tri1 = vértices 0,1,2  |  tri2 = vértices 0,2,3

def inicializaQuad():
    global Vao_quad

    Vao_quad = glGenVertexArrays(1)
    glBindVertexArray(Vao_quad)

    # Dados interleaved: posição (x,y,z) + UV (u,v) por vértice
    vertices = np.array([
        # x      y     z     u    v
        -0.5,  0.5,  0.0,  0.0, 1.0,   # vértice 0 - superior esquerdo
         0.5,  0.5,  0.0,  1.0, 1.0,   # vértice 1 - superior direito
         0.5, -0.5,  0.0,  1.0, 0.0,   # vértice 2 - inferior direito
        -0.5, -0.5,  0.0,  0.0, 0.0,   # vértice 3 - inferior esquerdo
    ], dtype=np.float32)

    # Índices que definem os 2 triângulos do quad
    indices = np.array([
        0, 1, 2,   # triângulo superior direito
        0, 2, 3,   # triângulo inferior esquerdo
    ], dtype=np.uint32)

    # ---- VBO (Vertex Buffer Object): envia os vértices para a GPU ----
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # ---- EBO (Element Buffer Object): envia os índices para a GPU ----
    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    # ---- Como interpretar os dados interleaved ----
    # Cada vértice ocupa 5 floats = 5 * 4 bytes = 20 bytes (stride)
    stride = 5 * 4  # 4 bytes por float

    # Atributo 0: posição (x, y, z) — começa no byte 0
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)

    # Atributo 1: coordenada UV (u, v) — começa após 3 floats = byte 12
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

# -----------------------------------------------
# Carregamento de textura
# -----------------------------------------------
# Aqui abrimos a imagem com Pillow, convertemos para RGBA e enviamos para a GPU.
# O OpenGL recebe os bytes crus da imagem e armazena na memória de vídeo.

def carregaTextura(caminho):
    global Textura_id

    # Abre a imagem e converte para RGBA (garante 4 canais: R, G, B, Alpha)
    img = Image.open(caminho).convert("RGBA")

    # OpenGL espera a imagem de baixo para cima (origem no canto inferior esquerdo)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    dados = np.array(img, dtype=np.uint8)
    largura, altura = img.size

    # Gera um ID de textura na GPU e o "ativa"
    Textura_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, Textura_id)

    # Parâmetros de filtragem:
    # GL_LINEAR = interpola pixels vizinhos (suave)
    # GL_NEAREST = pixel mais próximo (pixelado, estilo retro)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # Parâmetros de repetição:
    # GL_REPEAT = repete a textura se UV > 1  (como ladrilho)
    # GL_CLAMP_TO_EDGE = estica a borda
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)  # eixo U (horizontal)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)  # eixo V (vertical)

    # Envia os dados da imagem para a GPU
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, largura, altura, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, dados)

    # Gera mipmaps: versões menores da textura para quando o objeto está distante
    glGenerateMipmap(GL_TEXTURE_2D)

    print(f"Textura carregada: {caminho} ({largura}x{altura})")

# -----------------------------
# Shaders
# -----------------------------
# Novidades em relação ao exemplo base:
# - Atributo 1 (tex_coord): recebe as UVs do VBO
# - varying 'uv': passa as UVs do vertex para o fragment shader
# - uniform sampler2D textura: representa a textura no fragment shader
# - texture(textura, uv): faz a leitura da cor da textura nas coordenadas UV

def inicializaShaders():
    global Shader_programm

    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        layout(location = 1) in vec2 tex_coord;       // UV vindo do VBO

        uniform mat4 transform;

        out vec2 uv;    // passa para o fragment shader

        void main() {
            uv = tex_coord;
            gl_Position = transform * vec4(vertex_posicao, 1.0);
        }
    """

    fragment_shader = """
        #version 400
        in vec2 uv;                     // UV interpolado pelo rasterizador
        uniform sampler2D textura;      // representa a textura (unidade 0)

        out vec4 frag_colour;

        void main() {
            // texture() lê a cor da textura nas coordenadas UV do fragmento
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

    rotZ = np.array([
        [np.cos(rz), -np.sin(rz), 0, 0],
        [np.sin(rz),  np.cos(rz), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ], dtype=np.float32)

    escala = np.array([
        [Sx,  0,  0, 0],
        [ 0, Sy,  0, 0],
        [ 0,  0, Sz, 0],
        [ 0,  0,  0, 1]
    ], dtype=np.float32)

    transform = translacao @ rotZ @ escala

    loc = glGetUniformLocation(Shader_programm, "transform")
    glUniformMatrix4fv(loc, 1, GL_TRUE, transform)

# -----------------------------
# Renderização
# -----------------------------

def inicializaRenderizacao():
    tempo_anterior = glfw.get_time()

    while not glfw.window_should_close(Window):
        tempo_atual = glfw.get_time()
        delta = tempo_atual - tempo_anterior
        tempo_anterior = tempo_atual

        glClearColor(0.15, 0.15, 0.15, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)

        # Ativa a unidade de textura 0 e associa nossa textura a ela
        # O uniform 'textura' no shader aponta para a unidade 0 por padrão
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, Textura_id)
        glUniform1i(glGetUniformLocation(Shader_programm, "textura"), 0)

        glBindVertexArray(Vao_quad)

        # Quad centralizado, com leve rotação ao longo do tempo para animação
        angulo = tempo_atual * 30.0  # 30 graus por segundo
        transformacaoGenerica(0.0, 0.0, 0.0,  1.0, 1.0, 1.0,  0, 0, angulo)

        # glDrawElements usa o EBO para saber quais vértices desenhar
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

        glfw.swap_buffers(Window)
        glfw.poll_events()

    glfw.terminate()

# -----------------------------
# Função principal
# -----------------------------

def main():
    inicializaOpenGL()
    inicializaQuad()
    inicializaShaders()
    carregaTextura(CAMINHO_TEXTURA)
    inicializaRenderizacao()

if __name__ == "__main__":
    main()
