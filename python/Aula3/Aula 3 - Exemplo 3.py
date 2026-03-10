# Terreno com Nível de Detalhe Ajustável — exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra como a resolução de uma malha afeta diretamente
# a qualidade visual de uma superfície curva gerada proceduralmente.
#
# Um terreno é uma superfície definida por uma função de altura do tipo:
#   y = f(x, z)
# onde (x, z) é a posição horizontal e y é a altura naquele ponto.
#
# Alterar a resolução do grid altera:
#   - a quantidade de vértices amostrados da função de altura
#   - a quantidade de triângulos que formam a malha
#   - o nível de detalhe visual da superfície
#
# Controles:
#   W/A/S/D   — mover câmera (FPS)
#   Mouse     — girar câmera
#   +         — aumentar resolução do terreno (mais triângulos)
#   -         — diminuir resolução do terreno (menos triângulos)
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
Cam_pos   = np.array([0.0, 4.0, 10.0], dtype=np.float32)
Cam_yaw   = -90.0   # Aponta para o interior da cena (eixo -Z)
Cam_pitch = -25.0   # Inclina levemente para baixo para focar o terreno
Cam_speed = 8.0

lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

Tempo_entre_frames = 0.0  # variável utilizada para movimentar a câmera

# -----------------------------
# Estado do terreno
# -----------------------------

# Resolução da malha: número de divisões do grid em cada direção.
# Valores baixos  →  poucos triângulos, relevo blocado e impreciso
# Valores altos   →  muitos triângulos, relevo suave e detalhado
Resolucao_terreno = 10

# Referência ao VAO e ao EBO atuais do terreno (recriados ao mudar resolução)
Vao_terreno   = None
Ebo_terreno   = None
Qtd_indices   = 0

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

def key_callback(window, key, scancode, action, mode):
    global Resolucao_terreno

    if action != glfw.PRESS:
        return

    # + — aumenta o detalhe do terreno (mais subdivisões, mais triângulos)
    if key in (glfw.KEY_EQUAL, glfw.KEY_KP_ADD):
        if Resolucao_terreno < 200:
            Resolucao_terreno += 5
            inicializaTerreno()
            print(f"\n[TERRENO] Resolução: {Resolucao_terreno}x{Resolucao_terreno} → {Qtd_indices // 3} triângulos")

    # - — diminui o detalhe do terreno (menos subdivisões, menos triângulos)
    if key in (glfw.KEY_MINUS, glfw.KEY_KP_SUBTRACT):
        if Resolucao_terreno > 5:
            Resolucao_terreno -= 5
            inicializaTerreno()
            print(f"\n[TERRENO] Resolução: {Resolucao_terreno}x{Resolucao_terreno} → {Qtd_indices // 3} triângulos")

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
    Window = glfw.create_window(WIDTH, HEIGHT, 'Terreno — CG em Tempo Real', None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)
    glfw.set_key_callback(Window, key_callback)

    print("Placa de vídeo: ", glGetString(GL_RENDERER))
    print("Versão do OpenGL: ", glGetString(GL_VERSION))

# -----------------------------
# Função de altura do terreno
# -----------------------------

def altura(x, z):
    """
    Define a altura do terreno em cada ponto (x, z) do plano horizontal.

    O terreno é uma superfície do tipo y = f(x, z).
    Não há "forma pronta" — o relevo emerge inteiramente da avaliação
    desta função em vários pontos do espaço.

    Usamos uma combinação de seno e cosseno porque:
      - geram ondas suaves e contínuas
      - a soma de ondas com frequências diferentes produz relevo mais variado
      - são fáceis de controlar e visualizar

    Interpretação de cada parcela:
      - sin(x * 0.6)         → variação suave no eixo X
      - cos(z * 0.4)         → variação suave no eixo Z
      - sin((x + z) * 0.3)   → variação diagonal, cria morros "enviesados"

    Os fatores multiplicativos controlam:
      - a frequência (quantas ondulações cabem no espaço)
      - a amplitude  (altura máxima de cada onda)
    """
    return (
        np.sin(x * 0.6) * 1.5 +
        np.cos(z * 0.4) * 1.2 +
        np.sin((x + z) * 0.3) * 1.0
    )

# -----------------------------
# Geração da malha do terreno
# -----------------------------

def geraTerreno(res):
    """
    Gera a malha do terreno como um grid regular no plano XZ.

    Parâmetro 'res':
      - define quantas divisões o grid terá em cada direção
      - quanto maior 'res':
          * mais vértices amostrados da função de altura
          * mais triângulos na malha
          * mais detalhe visual na superfície

    Retorna:
      vertices — array de posições (x, y, z) de cada vértice
      indices  — array de índices que define os triângulos

    Geração dos vértices:
      Percorremos o grid linha por linha. Para cada posição (i, j),
      calculamos as coordenadas x e z no espaço, avaliamos a função
      de altura para obter y e armazenamos (x, y, z) como um vértice.
      Isso cria uma grade de pontos distribuídos regularmente.

    Geração dos triângulos:
      Cada célula da grade é um quadrado formado por quatro vértices:

        a ---- d
        |    / |
        |   /  |
        |  /   |
        b ---- c

      Como a GPU trabalha com triângulos, cada quadrado é dividido em dois:
        - triângulo 1: (a, b, c)
        - triângulo 2: (a, c, d)

      Esse padrão se repete por todo o terreno.
    """
    vertices = []
    indices  = []

    tamanho = 20.0          # extensão física do terreno no espaço
    passo   = tamanho / res # distância entre pontos adjacentes do grid

    # Amostragem da função de altura em cada ponto (i, j) do grid
    for i in range(res + 1):
        for j in range(res + 1):
            x = -tamanho / 2 + j * passo
            z = -tamanho / 2 + i * passo
            y = altura(x, z)
            vertices.extend([x, y, z])

    # Função auxiliar: converte coordenadas (linha, coluna) em índice linear
    def idx(i, j):
        return i * (res + 1) + j

    # Divisão de cada célula quadrada em dois triângulos
    for i in range(res):
        for j in range(res):
            a = idx(i,     j    )
            b = idx(i + 1, j    )
            c = idx(i + 1, j + 1)
            d = idx(i,     j + 1)

            indices.extend([a, b, c])   # triângulo 1
            indices.extend([a, c, d])   # triângulo 2

    return np.array(vertices, np.float32), np.array(indices, np.uint32)

# -----------------------------
# Inicialização da geometria
# -----------------------------

def inicializaTerreno():
    """
    Cria (ou recria) o VAO do terreno com a resolução atual.
    Chamada na inicialização e toda vez que o usuário pressiona +/-.
    """
    global Vao_terreno, Ebo_terreno, Qtd_indices

    # Libera o VAO anterior antes de criar um novo
    if Vao_terreno:
        glDeleteVertexArrays(1, [Vao_terreno])

    vertices, indices = geraTerreno(Resolucao_terreno)
    Qtd_indices = len(indices)

    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    # VBO — envia os vértices para a GPU
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # EBO — envia os índices de triângulos para a GPU
    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    # Atributo 0: posição (x, y, z) — 3 floats, stride = 12 bytes
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(0))

    Vao_terreno = vao
    Ebo_terreno = ebo

    glfw.set_window_title(
        Window,
        f'Terreno — resolução {Resolucao_terreno}x{Resolucao_terreno} | {Qtd_indices // 3} tri'
    )

# -----------------------------
# Shaders
# -----------------------------
# O vertex shader recebe apenas a posição do vértice e aplica as matrizes
# de visualização e projeção para posicioná-lo na tela.
#
# O fragment shader pinta todos os fragmentos com uma cor verde fixa —
# o foco deste exemplo é a malha e sua resolução, não a iluminação.

def inicializaShaders():
    global Shader_programm

    # Especificação do Vertex Shader:
    vertex_shader = """
        #version 330 core
        layout(location = 0) in vec3 vertex_posicao;
        // view  — matriz da câmera recebida do Python
        // proj  — matriz de projeção recebida do Python
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
        void main() {
            // Cor verde fixa — o foco é a malha, não a iluminação
            frag_colour = vec4(0.3, 0.7, 0.4, 1.0);
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
      - A partir de Cam_yaw e Cam_pitch, calculamos o vetor 'frente':
          ele aponta exatamente na direção para onde a câmera olha.
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
    zfar    = 200.0           # recorte z-far
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

    print("\n--- Exemplo: Terreno com Nível de Detalhe Ajustável ---")
    print("  +/-        — aumentar/diminuir resolução do terreno")
    print("  W/A/S/D + mouse — câmera FPS")
    print("  ESC        — fechar\n")
    print("  Observe: com resolução baixa, o relevo é blocado e impreciso.")
    print("  À medida que a resolução aumenta, a função de altura é amostrada")
    print("  em mais pontos e a superfície fica progressivamente mais suave.\n")

    while not glfw.window_should_close(Window):
        # Calcula quantos segundos se passaram entre um frame e outro
        tempo_frame_atual  = glfw.get_time()
        Tempo_entre_frames = tempo_frame_atual - tempo_anterior
        tempo_anterior     = tempo_frame_atual

        glClearColor(0.5, 0.75, 1.0, 1.0)  # fundo azul céu
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # limpa os buffers de cor e profundidade

        glUseProgram(Shader_programm)
        inicializaCamera()

        # Desenha o terreno usando índices (EBO)
        glBindVertexArray(Vao_terreno)
        glDrawElements(GL_TRIANGLES, Qtd_indices, GL_UNSIGNED_INT, None)

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

    glfw.terminate()

# Função principal
def main():
    inicializaOpenGL()
    inicializaShaders()
    inicializaTerreno()
    inicializaRenderizacao()

if __name__ == '__main__':
    main()