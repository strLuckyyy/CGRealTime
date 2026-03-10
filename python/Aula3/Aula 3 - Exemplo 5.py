# Bounding Volume (AABB) vs Malha Real — exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra a diferença entre a malha real de um objeto
# e uma geometria auxiliar chamada Bounding Volume (volume delimitador).
#
# Malha real:
#   - define a forma exata do objeto (aqui, uma esfera UV com muitos triângulos)
#   - é usada para renderização
#   - tem alto custo geométrico
#
# Bounding Volume (AABB — Axis-Aligned Bounding Box):
#   - é uma caixa alinhada aos eixos que envolve completamente o objeto
#   - não representa a forma real — apenas o volume mínimo que a contém
#   - tem custo geométrico muito baixo (8 vértices, 12 arestas)
#   - usada para decisões rápidas: visibilidade, colisão, culling
#
# A AABB é desenhada em wireframe para evidenciar que ela é uma aproximação,
# não a geometria real. A esfera real é desenhada como sólido.
#
# Controles:
#   W/A/S/D   — mover câmera (FPS)
#   Mouse     — girar câmera
#   ESC       — fechar

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import ctypes

# -----------------------------
# Configuração geral
# -----------------------------

WIDTH  = 1000
HEIGHT = 700

Window          = None
Shader_programm = None

# Câmera FPS
Cam_pos   = np.array([0.0, 0.0, 4.0], dtype=np.float32)
Cam_yaw   = -90.0  # Aponta para o interior da cena (eixo -Z)
Cam_pitch =   0.0
Cam_speed =   4.0

lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

Tempo_entre_frames = 0.0  # variável utilizada para movimentar a câmera

# -----------------------------
# Estado dos objetos
# -----------------------------

# Malha real da esfera (renderizada como sólido)
Vao_esfera          = None
Ebo_esfera          = None
Qtd_indices_esfera  = 0

# Geometria da AABB (renderizada em wireframe)
Vao_aabb            = None
Ebo_aabb            = None
Qtd_indices_aabb    = 0

# -----------------------------
# Callbacks de janela e entrada
# -----------------------------

def mouse_callback(window, xpos, ypos):
    global lastX, lastY, primeiro_mouse, Cam_yaw, Cam_pitch

    if primeiro_mouse:
        lastX, lastY   = xpos, ypos
        primeiro_mouse = False

    xoffset = xpos - lastX
    yoffset = lastY - ypos
    lastX, lastY = xpos, ypos

    sensibilidade = 0.1
    Cam_yaw   += xoffset * sensibilidade
    Cam_pitch += yoffset * sensibilidade

    Cam_pitch = max(-89.0, min(89.0, Cam_pitch))

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    # Inicializa GLFW
    glfw.init()
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    # Criação de uma janela
    Window = glfw.create_window(WIDTH, HEIGHT, 'Bounding Volume (AABB) — CG em Tempo Real', None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)

    print("Placa de vídeo: ", glGetString(GL_RENDERER))
    print("Versão do OpenGL: ", glGetString(GL_VERSION))

# -----------------------------
# Geometria da esfera
# -----------------------------

def geraEsferaUV(stacks, slices, raio=0.8):
    """
    Gera uma esfera UV parametrizada por dois ângulos: phi (vertical) e theta (horizontal).

    Parâmetros:
      stacks — número de divisões verticais (latitude)
      slices — número de divisões horizontais (longitude)
      raio   — raio da esfera

    A posição de cada vértice é calculada por:
      x = raio * sin(phi) * cos(theta)
      y = raio * cos(phi)
      z = raio * sin(phi) * sin(theta)

    Quanto maiores stacks e slices, mais triângulos e mais suave a superfície.
    A malha é indexada: vértices únicos no VBO, conectividade no EBO.
    """
    vertices = []
    indices  = []

    for i in range(stacks + 1):
        phi = np.pi * i / stacks
        for j in range(slices + 1):
            theta = 2 * np.pi * j / slices
            x = raio * np.sin(phi) * np.cos(theta)
            y = raio * np.cos(phi)
            z = raio * np.sin(phi) * np.sin(theta)
            vertices.extend([x, y, z])

    # Função auxiliar: converte (linha, coluna) em índice linear
    def idx(i, j):
        return i * (slices + 1) + j

    # Cada célula da grade esférica gera dois triângulos
    for i in range(stacks):
        for j in range(slices):
            a = idx(i,     j    )
            b = idx(i + 1, j    )
            c = idx(i + 1, j + 1)
            d = idx(i,     j + 1)
            indices.extend([a, b, c])
            indices.extend([a, c, d])

    return np.array(vertices, np.float32), np.array(indices, np.uint32)

# -----------------------------
# Geometria da AABB
# -----------------------------

def calculaAABB(vertices):
    """
    Calcula a Axis-Aligned Bounding Box (AABB) de uma malha.

    A AABB é definida por dois pontos:
      - min_v: o menor x, y e z encontrados entre todos os vértices
      - max_v: o maior x, y e z encontrados entre todos os vértices

    Ela é o menor paralelepípedo alinhado aos eixos que contém
    completamente a malha. Não representa a forma real do objeto —
    apenas o seu "envelope" retangular.
    """
    verts = vertices.reshape(-1, 3)
    min_v = verts.min(axis=0)
    max_v = verts.max(axis=0)
    return min_v, max_v


def geraAABB(min_v, max_v):
    """
    Cria a geometria de arame (wireframe) de uma AABB.

    A caixa possui:
      - 8 vértices, um em cada canto
      - 12 arestas representadas por 24 índices para GL_LINES

    Cada par de índices no EBO define uma aresta:
      - 4 arestas na face frontal
      - 4 arestas na face traseira
      - 4 arestas conectando frente e trás
    """
    vertices = [
        min_v[0], min_v[1], min_v[2],   # 0 — baixo-trás-esq
        max_v[0], min_v[1], min_v[2],   # 1 — baixo-trás-dir
        max_v[0], max_v[1], min_v[2],   # 2 — cima-trás-dir
        min_v[0], max_v[1], min_v[2],   # 3 — cima-trás-esq

        min_v[0], min_v[1], max_v[2],   # 4 — baixo-frente-esq
        max_v[0], min_v[1], max_v[2],   # 5 — baixo-frente-dir
        max_v[0], max_v[1], max_v[2],   # 6 — cima-frente-dir
        min_v[0], max_v[1], max_v[2],   # 7 — cima-frente-esq
    ]

    indices = [
        0,1,  1,2,  2,3,  3,0,   # arestas da face traseira
        4,5,  5,6,  6,7,  7,4,   # arestas da face frontal
        0,4,  1,5,  2,6,  3,7,   # arestas laterais (conectam frente e trás)
    ]

    return np.array(vertices, np.float32), np.array(indices, np.uint32)

# -----------------------------
# Inicialização das geometrias
# -----------------------------

def inicializaGeometria():
    global Vao_esfera, Ebo_esfera, Qtd_indices_esfera
    global Vao_aabb, Ebo_aabb, Qtd_indices_aabb

    # -------- Esfera (malha real) --------
    vertices, indices = geraEsferaUV(48, 48)
    min_v, max_v      = calculaAABB(vertices)   # calcula a AABB a partir dos vértices reais

    Vao_esfera = glGenVertexArrays(1)
    glBindVertexArray(Vao_esfera)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    Ebo_esfera = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, Ebo_esfera)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    # Atributo 0: posição (x, y, z) — 3 floats, stride = 12 bytes
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))

    Qtd_indices_esfera = len(indices)

    # -------- AABB (bounding volume) --------
    v_aabb, i_aabb = geraAABB(min_v, max_v)

    Vao_aabb = glGenVertexArrays(1)
    glBindVertexArray(Vao_aabb)

    vbo_aabb = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_aabb)
    glBufferData(GL_ARRAY_BUFFER, v_aabb.nbytes, v_aabb, GL_STATIC_DRAW)

    Ebo_aabb = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, Ebo_aabb)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, i_aabb.nbytes, i_aabb, GL_STATIC_DRAW)

    # Atributo 0: posição (x, y, z) — 3 floats, stride = 12 bytes
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))

    Qtd_indices_aabb = len(i_aabb)

# -----------------------------
# Shaders
# -----------------------------
# O vertex shader recebe apenas a posição do vértice e aplica as matrizes
# de visualização e projeção para posicioná-lo na tela.
#
# O fragment shader pinta cada fragmento com uma cor uniforme passada pelo Python.
# Não há iluminação — o foco é a geometria (malha vs bounding volume).

def inicializaShaders():
    global Shader_programm

    # Especificação do Vertex Shader:
    vertex_shader = """
        #version 330 core
        layout(location = 0) in vec3 vertex_posicao;
        // view — matriz da câmera recebida do Python
        // proj — matriz de projeção recebida do Python
        uniform mat4 view, proj;
        void main() {
            gl_Position = proj * view * vec4(vertex_posicao, 1.0);
        }
    """
    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    if not glGetShaderiv(vs, GL_COMPILE_STATUS):
        print("Erro no vertex shader:\n", glGetShaderInfoLog(vs, 512, None))

    # Especificação do Fragment Shader:
    fragment_shader = """
        #version 330 core
        out vec4 frag_colour;
        uniform vec4 corobjeto;
        void main() {
            frag_colour = corobjeto;
        }
    """
    fs = OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    if not glGetShaderiv(fs, GL_COMPILE_STATUS):
        print("Erro no fragment shader:\n", glGetShaderInfoLog(fs, 512, None))

    # Especificação do Shader Program:
    Shader_programm = OpenGL.GL.shaders.compileProgram(vs, fs)
    if not glGetProgramiv(Shader_programm, GL_LINK_STATUS):
        print("Erro na linkagem do shader:\n", glGetProgramInfoLog(Shader_programm, 512, None))

    glDeleteShader(vs)
    glDeleteShader(fs)

# -----------------------------
# Câmera (matriz de visualização)
# -----------------------------

def especificaMatrizVisualizacao():
    """
    Implementa um sistema de câmera no estilo FPS usando uma matriz lookAt manual.

    A ideia geral é simular uma câmera no espaço 3D: um ponto (posição) e uma
    direção (para onde ela está olhando). Em vez de mover a câmera, aplicamos
    a transformação inversa no mundo — deslocamos e rotacionamos tudo o que é
    desenhado, como se a câmera estivesse fixa na origem.

    Etapas:
      - A partir de Cam_yaw e Cam_pitch, calculamos o vetor 'frente'.
      - O vetor 'direita' é o produto vetorial entre 'frente' e o eixo Y mundial.
      - O vetor 'cima' é o produto vetorial entre 'direita' e 'frente'.

    Montagem da matriz:
          |  sx   sy   sz  -dot(s, pos) |
          |  ux   uy   uz  -dot(u, pos) |
          | -fx  -fy  -fz   dot(f, pos) |
          |   0    0    0       1       |
    """
    frente = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ], dtype=np.float32)
    frente /= np.linalg.norm(frente)

    centro = Cam_pos + frente
    cima   = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    f = centro - Cam_pos;  f /= np.linalg.norm(f)
    s = np.cross(f, cima); s /= np.linalg.norm(s)
    u = np.cross(s, f)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] =  s
    view[1, :3] =  u
    view[2, :3] = -f
    view[0,  3] = -np.dot(s, Cam_pos)
    view[1,  3] = -np.dot(u, Cam_pos)
    view[2,  3] =  np.dot(f, Cam_pos)

    transformLoc = glGetUniformLocation(Shader_programm, "view")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, view)

# -----------------------------
# Projeção
# -----------------------------

def especificaMatrizProjecao():
    # Especificação da matriz de projeção perspectiva.
    znear   = 0.1             # recorte z-near
    zfar    = 100.0           # recorte z-far
    fov     = np.radians(67.0)  # campo de visão
    aspecto = WIDTH / HEIGHT    # aspecto da janela

    a = 1.0 / (np.tan(fov / 2) * aspecto)
    b = 1.0 /  np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)

    projecao = np.array([
        [a,   0.0, 0.0,  0.0],
        [0.0, b,   0.0,  0.0],
        [0.0, 0.0, c,    d  ],
        [0.0, 0.0, -1.0, 1.0]
    ], dtype=np.float32)

    transformLoc = glGetUniformLocation(Shader_programm, "proj")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, projecao)

def inicializaCamera():
    especificaMatrizVisualizacao()  # posição e orientação da câmera
    especificaMatrizProjecao()      # perspectiva

# -----------------------------
# Definição de cor
# -----------------------------

def defineCor(r, g, b, a):
    # Passa a cor do objeto para o fragment shader como uniform
    cores    = np.array([r, g, b, a], dtype=np.float32)
    coresLoc = glGetUniformLocation(Shader_programm, "corobjeto")
    glUniform4fv(coresLoc, 1, cores)

# -----------------------------
# Entrada de teclado
# -----------------------------

def trataTeclado():
    """
    Movimenta a câmera no espaço 3D conforme as teclas WASD.
    A direção do movimento segue o vetor 'frente' (para onde o jogador está
    olhando), incluindo a inclinação vertical (pitch).
    """
    global Cam_pos

    velocidade = Cam_speed * Tempo_entre_frames

    frente = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ], dtype=np.float32)
    frente /= np.linalg.norm(frente)

    direita = np.cross(frente, np.array([0.0, 1.0, 0.0], dtype=np.float32))
    direita /= np.linalg.norm(direita)

    # W/S: movem para frente/trás na direção atual da câmera
    if glfw.get_key(Window, glfw.KEY_W) == glfw.PRESS:
        Cam_pos += frente * velocidade
    if glfw.get_key(Window, glfw.KEY_S) == glfw.PRESS:
        Cam_pos -= frente * velocidade

    # A/D: movem lateralmente em relação à direção da câmera
    if glfw.get_key(Window, glfw.KEY_A) == glfw.PRESS:
        Cam_pos -= direita * velocidade
    if glfw.get_key(Window, glfw.KEY_D) == glfw.PRESS:
        Cam_pos += direita * velocidade

    if glfw.get_key(Window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(Window, True)

# -----------------------------
# Loop de renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames

    tempo_anterior = glfw.get_time()

    # Ativa o teste de profundidade para que faces mais próximas sobreponham as mais distantes
    glEnable(GL_DEPTH_TEST)

    print("\n--- Exemplo: Bounding Volume (AABB) vs Malha Real ---")
    print("  Azul  — esfera UV (malha real, sólido): forma exata, alto custo geométrico")
    print("  Vermelho — AABB (wireframe): aproximação retangular, custo mínimo")
    print("  Observe que a caixa envolve completamente a esfera em todos os ângulos.\n")
    print("  W/A/S/D + mouse — câmera FPS")
    print("  ESC             — fechar\n")

    while not glfw.window_should_close(Window):
        # Calcula quantos segundos se passaram entre um frame e outro
        tempo_frame_atual  = glfw.get_time()
        Tempo_entre_frames = tempo_frame_atual - tempo_anterior
        tempo_anterior     = tempo_frame_atual

        glClearColor(0.15, 0.18, 0.22, 1.0)  # define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # limpa os buffers de cor e profundidade

        glUseProgram(Shader_programm)
        inicializaCamera()

        # --- Esfera (malha real) — azul, sólido ---
        # Desenhada com a forma exata: muitos triângulos, superfície suave.
        defineCor(0.3, 0.7, 0.9, 1.0)
        glBindVertexArray(Vao_esfera)
        glDrawElements(GL_TRIANGLES, Qtd_indices_esfera, GL_UNSIGNED_INT, None)

        # --- AABB (bounding volume) — vermelho, wireframe ---
        # Desenhada como arame para evidenciar que é uma aproximação,
        # não a geometria real. Envolve completamente a esfera.
        defineCor(1.0, 0.2, 0.2, 1.0)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glBindVertexArray(Vao_aabb)
        glDrawElements(GL_LINES, Qtd_indices_aabb, GL_UNSIGNED_INT, None)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)  # restaura o modo de preenchimento

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

    glfw.terminate()

# Função principal
def main():
    inicializaOpenGL()
    inicializaShaders()
    inicializaGeometria()
    inicializaRenderizacao()

if __name__ == '__main__':
    main()