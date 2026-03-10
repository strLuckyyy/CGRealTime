# Cubo com e sem Índice — exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra que o mesmo objeto (um cubo) pode ser representado
# de duas formas diferentes na GPU:
#
# 1) Sem índice — glDrawArrays:
#      - cada triângulo declara seus próprios três vértices
#      - vértices que pertencem a múltiplas faces são duplicados na memória
#      - cubo com 6 faces × 2 triângulos × 3 vértices = 36 vértices no VBO
#
# 2) Com índice — glDrawElements:
#      - cada posição única é armazenada apenas uma vez (8 vértices no total)
#      - um buffer de índices (EBO) diz à GPU quais vértices compõem cada triângulo
#      - conectividade e posição são separadas: o EBO conecta, o VBO posiciona
#
# Visualmente os dois cubos são idênticos.
# Estruturalmente são completamente diferentes.
# A versão indexada é mais eficiente — especialmente em malhas grandes,
# onde o compartilhamento de vértices reduz drasticamente o uso de memória.
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
Cam_pos   = np.array([0.0, 1.5, 6.0], dtype=np.float32)
Cam_yaw   = -90.0  # Aponta para o interior da cena (eixo -Z)
Cam_pitch = -10.0  # Inclina levemente para baixo
Cam_speed = 5.0

lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

Tempo_entre_frames = 0.0  # variável utilizada para movimentar a câmera

# -----------------------------
# Estado dos objetos
# -----------------------------

# VAO do cubo sem índice — usa glDrawArrays (vértices duplicados)
Vao_sem_indice = None

# VAO do cubo com índice — usa glDrawElements (vértices compartilhados)
Vao_com_indice = None
Ebo_com_indice = None

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
    Window = glfw.create_window(WIDTH, HEIGHT, 'Cubo com e sem Índice — CG em Tempo Real', None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)

    print("Placa de vídeo: ", glGetString(GL_RENDERER))
    print("Versão do OpenGL: ", glGetString(GL_VERSION))

# -----------------------------
# Geometria do cubo
# -----------------------------

def criaCubeSemIndice():
    """
    Constrói um cubo descrito apenas por vértices, sem EBO.

    Cada face do cubo possui seus próprios vértices declarados explicitamente.
    Isso significa que vértices compartilhados entre faces são duplicados:
    um cubo tem 8 vértices únicos, mas aqui usamos 36 (6 faces × 2 tri × 3 verts).

    Essa abordagem é simples, mas ineficiente:
      - a GPU recebe mais dados que o necessário
      - não há reutilização de vértices entre triângulos adjacentes
      - em malhas grandes, o desperdício de memória é expressivo
    """
    vertices = [
        # face frontal (+Z) — dois triângulos
        -1,-1, 1,   1,-1, 1,   1, 1, 1,
        -1,-1, 1,   1, 1, 1,  -1, 1, 1,

        # face traseira (-Z)
        -1,-1,-1,  -1, 1,-1,   1, 1,-1,
        -1,-1,-1,   1, 1,-1,   1,-1,-1,

        # face esquerda (-X)
        -1,-1,-1,  -1,-1, 1,  -1, 1, 1,
        -1,-1,-1,  -1, 1, 1,  -1, 1,-1,

        # face direita (+X)
         1,-1,-1,   1, 1,-1,   1, 1, 1,
         1,-1,-1,   1, 1, 1,   1,-1, 1,

        # face superior (+Y)
        -1, 1,-1,  -1, 1, 1,   1, 1, 1,
        -1, 1,-1,   1, 1, 1,   1, 1,-1,

        # face inferior (-Y)
        -1,-1,-1,   1,-1,-1,   1,-1, 1,
        -1,-1,-1,   1,-1, 1,  -1,-1, 1,
    ]

    return np.array(vertices, np.float32)


def criaCubeComIndice():
    """
    Constrói um cubo descrito por 8 vértices únicos + um buffer de índices (EBO).

    Em vez de duplicar posições, armazenamos cada vértice apenas uma vez.
    O EBO lista, para cada triângulo, quais três índices do VBO ele utiliza.

    Resultado:
      - VBO: 8 vértices (o mínimo possível para um cubo)
      - EBO: 36 índices (6 faces × 2 tri × 3 verts) — cada índice é um inteiro pequeno
      - A GPU reutiliza vértices ao montar os triângulos

    Em cenas reais (malhas com milhares de vértices), essa economia
    de memória e largura de banda tem impacto direto no desempenho.
    """
    vertices = [
        -1,-1, 1,   # 0 — frente-baixo-esq
         1,-1, 1,   # 1 — frente-baixo-dir
         1, 1, 1,   # 2 — frente-cima-dir
        -1, 1, 1,   # 3 — frente-cima-esq
        -1,-1,-1,   # 4 — trás-baixo-esq
         1,-1,-1,   # 5 — trás-baixo-dir
         1, 1,-1,   # 6 — trás-cima-dir
        -1, 1,-1,   # 7 — trás-cima-esq
    ]

    indices = [
        0,1,2,  0,2,3,   # frontal
        4,7,6,  4,6,5,   # traseira
        4,0,3,  4,3,7,   # esquerda
        1,5,6,  1,6,2,   # direita
        3,2,6,  3,6,7,   # superior
        4,5,1,  4,1,0,   # inferior
    ]

    return np.array(vertices, np.float32), np.array(indices, np.uint32)

# -----------------------------
# Inicialização das geometrias
# -----------------------------

def inicializaGeometria():
    global Vao_sem_indice, Vao_com_indice, Ebo_com_indice

    # -------- Cubo sem índice (glDrawArrays) --------
    vertices = criaCubeSemIndice()

    Vao_sem_indice = glGenVertexArrays(1)
    glBindVertexArray(Vao_sem_indice)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Atributo 0: posição (x, y, z) — 3 floats, stride = 12 bytes
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))

    # -------- Cubo com índice (glDrawElements) --------
    vertices_i, indices_i = criaCubeComIndice()

    Vao_com_indice = glGenVertexArrays(1)
    glBindVertexArray(Vao_com_indice)

    vbo_i = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_i)
    glBufferData(GL_ARRAY_BUFFER, vertices_i.nbytes, vertices_i, GL_STATIC_DRAW)

    Ebo_com_indice = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, Ebo_com_indice)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices_i.nbytes, indices_i, GL_STATIC_DRAW)

    # Atributo 0: posição (x, y, z) — 3 floats, stride = 12 bytes
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))

# -----------------------------
# Shaders
# -----------------------------
# O vertex shader recebe a posição do vértice e aplica as matrizes de câmera,
# projeção e transformação de modelo para posicioná-lo na tela.
#
# O fragment shader pinta cada fragmento com uma cor uniforme passada pelo Python.
# Não há iluminação — o foco é a estrutura da malha, não o sombreamento.

def inicializaShaders():
    global Shader_programm

    # Especificação do Vertex Shader:
    vertex_shader = """
        #version 330 core
        layout(location = 0) in vec3 vertex_posicao;
        // transform — matriz de modelo (translação do cubo)
        // view      — matriz da câmera recebida do Python
        // proj      — matriz de projeção recebida do Python
        uniform mat4 transform, view, proj;
        void main() {
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
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
# Transformação de modelo
# -----------------------------

def translacao(tx, ty, tz):
    # Matriz de translação — desloca o objeto na cena
    m = np.identity(4, dtype=np.float32)
    m[0, 3] = tx
    m[1, 3] = ty
    m[2, 3] = tz
    return m

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

    print("\n--- Exemplo: Cubo com e sem Índice ---")
    print("  Vermelho (esquerda) — sem índice: 36 vértices, glDrawArrays")
    print("  Verde    (direita)  — com índice:  8 vértices + EBO, glDrawElements")
    print("  Visualmente idênticos. Estruturalmente diferentes.\n")
    print("  W/A/S/D + mouse — câmera FPS")
    print("  ESC             — fechar\n")

    while not glfw.window_should_close(Window):
        # Calcula quantos segundos se passaram entre um frame e outro
        tempo_frame_atual  = glfw.get_time()
        Tempo_entre_frames = tempo_frame_atual - tempo_anterior
        tempo_anterior     = tempo_frame_atual

        glClearColor(0.2, 0.3, 0.4, 1.0)  # define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # limpa os buffers de cor e profundidade

        glUseProgram(Shader_programm)
        inicializaCamera()

        # --- Cubo sem índice (esquerda) — vermelho ---
        # Renderizado com glDrawArrays: a GPU lê os vértices sequencialmente,
        # sem reutilização. Simples, mas com vértices duplicados no VBO.
        defineCor(0.9, 0.4, 0.4, 1.0)
        transformLoc = glGetUniformLocation(Shader_programm, "transform")
        glUniformMatrix4fv(transformLoc, 1, GL_TRUE, translacao(-2, 0, 0))
        glBindVertexArray(Vao_sem_indice)
        glDrawArrays(GL_TRIANGLES, 0, 36)

        # --- Cubo com índice (direita) — verde ---
        # Renderizado com glDrawElements: a GPU segue os índices do EBO
        # para montar cada triângulo, reutilizando os 8 vértices únicos.
        defineCor(0.4, 0.9, 0.4, 1.0)
        glUniformMatrix4fv(transformLoc, 1, GL_TRUE, translacao(2, 0, 0))
        glBindVertexArray(Vao_com_indice)
        glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_INT, None)

        glfw.poll_events()
        glfw.swap_buffers(Window)
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