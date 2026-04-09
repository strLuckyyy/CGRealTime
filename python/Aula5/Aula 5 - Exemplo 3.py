# Debug Visual do Frustum Culling — exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo é uma extensão didática do Exemplo 4 (Frustum Culling).
# O objetivo aqui não é mostrar o ganho de desempenho, mas tornar o culling
# VISÍVEL — responder à pergunta: "o que exatamente está sendo descartado?"
#
# Novidades em relação ao Exemplo 4:
# - Câmera de jogo (Cam_jogo) separada da câmera de debug (Cam_debug):
#     A câmera de jogo pode ser TRAVADA no lugar (tecla T).
#     Com ela travada, você pilota a câmera de debug ao redor da cena e
#     enxerga o frustum da câmera de jogo como um objeto no mundo.
# - Wireframe amarelo do frustum:
#     As 12 arestas da pirâmide truncada (frustum) são desenhadas no espaço do mundo.
#     Qualquer cubo fora desse volume está sendo descartado.
# - Objetos culled em vermelho semitransparente:
#     Cubos fora do frustum são desenhados em vermelho translúcido (modo raio-x),
#     revelando o que normalmente seria invisível — e portanto descartado.
#
# Controles:
#   W/A/S/D + Mouse  — mover câmera ATIVA (jogo ou debug, dependendo do modo)
#   T                — travar/destravar câmera de jogo (ativa câmera de debug)
#   C                — alternar frustum culling (objetos culled ficam vermelhos ou somem)
#   +/-              — mais/menos objetos na cena
#   ESC              — fechar
#
# HUD no terminal (a cada ~1 segundo):
#   Modo câmera, culling, objetos na cena, desenhados, culled, FPS

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np

Window          = None
Shader_programm = None
Vao_cubo        = None
Vao_frustum     = None  # VAO das arestas do wireframe do frustum
WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0  # variavel utilizada para movimentar a camera

# -----------------------------
# Câmera de JOGO — é esta que define o frustum de culling
# -----------------------------
# Pode ser travada no lugar (Cam_jogo_travada = True).
# Quando travada, o frustum fica fixo no mundo e a câmera de debug orbita ao redor.

Cam_jogo_pos   = np.array([0.0, 0.0, 30.0], dtype=np.float32)
Cam_jogo_yaw   = 180.0  # olhando para a cena
Cam_jogo_pitch = 0.0
Cam_jogo_travada = False  # False = câmera de jogo é a ativa; True = debug é a ativa

# -----------------------------
# Câmera de DEBUG — só fica ativa quando a câmera de jogo está travada
# -----------------------------
# Permite orbitar a cena e ver o frustum da câmera de jogo de fora.

Cam_debug_pos   = np.array([0.0, 20.0, 60.0], dtype=np.float32)
Cam_debug_yaw   = 200.0
Cam_debug_pitch = -15.0

# Variáveis compartilhadas de mouse (sempre referem à câmera ativa)
lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# Velocidade de movimento
Cam_speed = 20.0  # velocidade da camera, 20 unidades por segundo

# Projeção — parâmetros globais usados tanto para a matriz de projeção
# quanto para extrair os planos e construir o wireframe do frustum
Cam_fov   = 67.0   # campo de visão em graus
Cam_znear = 0.1    # plano de corte próximo
Cam_zfar  = 80.0   # plano de corte distante (reduzido para o frustum ser mais visível na cena)

# -----------------------------
# Estado da demonstração
# -----------------------------

# True  → frustum culling ativado (objetos culled ficam vermelhos semitransparentes)
# False → culling desativado (todos os objetos são desenhados em azul normalmente)
Frustum_culling_ativo = True

# Número de objetos na cena
Num_objetos = 150

# Lista de posições dos objetos (gerada uma vez com seed fixa)
Objetos_posicoes = []  # lista de np.array([x, y, z])

# Raio do bounding volume de cada objeto (cubos unitários, raio = sqrt(3)/2)
Bounding_raio = np.sqrt(3) / 2

# Contadores do último frame
Objetos_desenhados = 0
Objetos_culled     = 0

# Acumuladores de FPS para o HUD
_fps_acumulado = 0.0
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
    global lastX, lastY, primeiro_mouse
    global Cam_jogo_yaw, Cam_jogo_pitch, Cam_debug_yaw, Cam_debug_pitch

    if primeiro_mouse:
        lastX, lastY   = xpos, ypos
        primeiro_mouse = False

    xoffset = xpos - lastX
    yoffset = lastY - ypos
    lastX, lastY = xpos, ypos

    sensibilidade = 0.1
    xoffset *= sensibilidade
    yoffset *= sensibilidade

    # O mouse controla a câmera ativa no momento
    if not Cam_jogo_travada:
        Cam_jogo_yaw   += xoffset
        Cam_jogo_pitch += yoffset
        Cam_jogo_pitch  = max(-89.0, min(89.0, Cam_jogo_pitch))
    else:
        Cam_debug_yaw   += xoffset
        Cam_debug_pitch += yoffset
        Cam_debug_pitch  = max(-89.0, min(89.0, Cam_debug_pitch))

def key_callback(window, key, scancode, action, mode):
    global Frustum_culling_ativo, Num_objetos, Cam_jogo_travada, primeiro_mouse

    if action != glfw.PRESS:
        return

    # T — trava/destrava a câmera de jogo
    if key == glfw.KEY_T:
        Cam_jogo_travada = not Cam_jogo_travada
        primeiro_mouse   = True  # reseta o mouse ao trocar de câmera (evita salto)
        estado = "TRAVADA (câmera de debug ativa)" if Cam_jogo_travada else "LIVRE (câmera de jogo ativa)"
        print(f"\n[CÂMERA] Câmera de jogo {estado}")
        if Cam_jogo_travada:
            print("         → Você agora vê o frustum da câmera de jogo no mundo!")

    # C — alterna frustum culling
    if key == glfw.KEY_C:
        Frustum_culling_ativo = not Frustum_culling_ativo
        estado = "ATIVADO (culled = vermelho)" if Frustum_culling_ativo else "DESATIVADO (tudo azul)"
        print(f"\n[CULLING] Frustum culling {estado}")

    # + / = — mais objetos
    if key in (glfw.KEY_EQUAL, glfw.KEY_KP_ADD):
        Num_objetos = min(Num_objetos + 50, 2000)
        geraObjetos()
        print(f"\n[OBJETOS] {Num_objetos} objetos na cena")

    # - — menos objetos
    if key in (glfw.KEY_MINUS, glfw.KEY_KP_SUBTRACT):
        Num_objetos = max(Num_objetos - 50, 50)
        geraObjetos()
        print(f"\n[OBJETOS] {Num_objetos} objetos na cena")

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    # Inicializa GLFW
    glfw.init()

    # Criação de uma janela
    Window = glfw.create_window(WIDTH, HEIGHT, "Debug Visual — Frustum Culling", None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.set_window_size_callback(Window, redimensionaCallback)
    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)
    glfw.set_key_callback(Window, key_callback)

    print("Placa de vídeo: ", glGetString(GL_RENDERER))
    print("Versão do OpenGL: ", glGetString(GL_VERSION))

# -----------------------------
# Inicialização da geometria: cubo unitário
# -----------------------------

def inicializaCubo():
    global Vao_cubo

    Vao_cubo = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo)

    # VBO dos vértices do cubo (36 vértices)
    points = [
        # face frontal
        0.5, 0.5, 0.5,   0.5, -0.5, 0.5,   -0.5, -0.5, 0.5,
        -0.5, 0.5, 0.5,  0.5,  0.5, 0.5,   -0.5, -0.5, 0.5,
        # face traseira
        0.5, 0.5, -0.5,  0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,
        -0.5, 0.5, -0.5, 0.5,  0.5, -0.5,  -0.5, -0.5, -0.5,
        # face esquerda
        -0.5, -0.5,  0.5,  -0.5,  0.5,  0.5,  -0.5, -0.5, -0.5,
        -0.5, -0.5, -0.5,  -0.5,  0.5, -0.5,  -0.5,  0.5,  0.5,
        # face direita
        0.5, -0.5,  0.5,   0.5,  0.5,  0.5,   0.5, -0.5, -0.5,
        0.5, -0.5, -0.5,   0.5,  0.5, -0.5,   0.5,  0.5,  0.5,
        # face baixo
        -0.5, -0.5,  0.5,  0.5, -0.5,  0.5,   0.5, -0.5, -0.5,
         0.5, -0.5, -0.5, -0.5, -0.5, -0.5,  -0.5, -0.5,  0.5,
        # face cima
        -0.5, 0.5,  0.5,   0.5,  0.5,  0.5,   0.5,  0.5, -0.5,
         0.5, 0.5, -0.5,  -0.5,  0.5, -0.5,  -0.5,  0.5,  0.5,
    ]
    points = np.array(points, dtype=np.float32)
    pvbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, pvbo)
    glBufferData(GL_ARRAY_BUFFER, points, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

# -----------------------------
# Cálculo dos 8 vértices do frustum no espaço do mundo
# -----------------------------
# O frustum é uma pirâmide truncada definida por dois retângulos:
# um pequeno (plano Near) e um grande (plano Far), centrados na direção 'front'.
#
# Os 8 vértices são calculados a partir dos vetores da câmera de JOGO
# (não da câmera de debug), pois é o frustum de jogo que queremos visualizar.
#
#   nlt, nrt, nlb, nrb = Near Left Top, Near Right Top, Near Left Bottom, Near Right Bottom
#   flt, frt, flb, frb = Far  Left Top, Far  Right Top, Far  Left Bottom, Far  Right Bottom

def calculaVerticesFrustum():
    fov_rad  = np.radians(Cam_fov)
    aspecto  = WIDTH / HEIGHT
    tang     = np.tan(fov_rad / 2)

    # Dimensões dos planos Near e Far
    hn = Cam_znear * tang   # meia-altura do near plane
    wn = hn * aspecto        # meia-largura do near plane
    hf = Cam_zfar  * tang   # meia-altura do far plane
    wf = hf * aspecto        # meia-largura do far plane

    # Vetores da câmera de JOGO
    front = np.array([
        np.cos(np.radians(Cam_jogo_yaw)) * np.cos(np.radians(Cam_jogo_pitch)),
        np.sin(np.radians(Cam_jogo_pitch)),
        np.sin(np.radians(Cam_jogo_yaw)) * np.cos(np.radians(Cam_jogo_pitch))
    ], dtype=np.float32)
    front = front / np.linalg.norm(front)

    right = np.cross(front, np.array([0.0, 1.0, 0.0], dtype=np.float32))
    right = right / np.linalg.norm(right)

    up = np.cross(right, front)
    up = up / np.linalg.norm(up)

    # Centros dos planos Near e Far no espaço do mundo
    centro_near = Cam_jogo_pos + front * Cam_znear
    centro_far  = Cam_jogo_pos + front * Cam_zfar

    # 4 vértices do plano Near
    nlt = centro_near + up * hn - right * wn  # near left  top
    nrt = centro_near + up * hn + right * wn  # near right top
    nlb = centro_near - up * hn - right * wn  # near left  bottom
    nrb = centro_near - up * hn + right * wn  # near right bottom

    # 4 vértices do plano Far
    flt = centro_far + up * hf - right * wf   # far left  top
    frt = centro_far + up * hf + right * wf   # far right top
    flb = centro_far - up * hf - right * wf   # far left  bottom
    frb = centro_far - up * hf + right * wf   # far right bottom

    return nlt, nrt, nlb, nrb, flt, frt, flb, frb

# -----------------------------
# Inicialização e atualização do VAO do wireframe do frustum
# -----------------------------
# O frustum é desenhado como 12 arestas em GL_LINES.
# Como o frustum muda a cada frame (câmera de jogo pode se mover),
# o VBO é atualizado dinamicamente via glBufferSubData.
#
# As 12 arestas são:
#   4 arestas do near plane  (quadrilátero frontal)
#   4 arestas do far plane   (quadrilátero traseiro)
#   4 arestas laterais ligando near ao far (as "bordas" do tronco)

def inicializaFrustumWireframe():
    global Vao_frustum

    Vao_frustum = glGenVertexArrays(1)
    glBindVertexArray(Vao_frustum)

    # Reserva espaço para 24 vértices (12 arestas × 2 pontos), 3 floats cada
    pvbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, pvbo)
    glBufferData(GL_ARRAY_BUFFER, 24 * 3 * 4, None, GL_DYNAMIC_DRAW)  # GL_DYNAMIC_DRAW: atualizado todo frame
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

def atualizaFrustumWireframe():
    # Recalcula os 8 vértices do frustum com a posição atual da câmera de jogo
    nlt, nrt, nlb, nrb, flt, frt, flb, frb = calculaVerticesFrustum()

    # Monta as 12 arestas como pares de vértices (24 pontos no total)
    arestas = np.array([
        # 4 arestas do near plane
        nlt, nrt,   nrt, nrb,   nrb, nlb,   nlb, nlt,
        # 4 arestas do far plane
        flt, frt,   frt, frb,   frb, flb,   flb, flt,
        # 4 arestas laterais (near → far)
        nlt, flt,   nrt, frt,   nrb, frb,   nlb, flb,
    ], dtype=np.float32).flatten()

    glBindVertexArray(Vao_frustum)
    glBufferSubData(GL_ARRAY_BUFFER, 0, arestas.nbytes, arestas)  # atualiza apenas os dados, sem realocar

# -----------------------------
# Shaders
# -----------------------------
# Idênticos ao exemplo base.

def inicializaShaders():
    global Shader_programm

    # Especificação do Vertex Shader:
    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        //view - matriz da câmera recebida do PYTHON
        //proj - matriz de projeção recebida do PYTHON
        //transform - matriz de transformação geométrica do objeto recebida do PYTHON
        uniform mat4 transform, view, proj;
        void main () {
            gl_Position = proj*view*transform*vec4(vertex_posicao, 1.0);
        }
    """
    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    if not glGetShaderiv(vs, GL_COMPILE_STATUS):
        print("Erro no vertex shader:\n", glGetShaderInfoLog(vs, 512, None))

    # Especificação do Fragment Shader:
    fragment_shader = """
        #version 400
        out vec4 frag_colour;
        uniform vec4 corobjeto;
        void main () {
            frag_colour = corobjeto;
        }
    """
    fs = OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    if not glGetShaderiv(fs, GL_COMPILE_STATUS):
        print("Erro no fragment shader:\n", glGetShaderInfoLog(fs, 512, None))

    # Especificação do Shader Programm:
    Shader_programm = OpenGL.GL.shaders.compileProgram(vs, fs)
    if not glGetProgramiv(Shader_programm, GL_LINK_STATUS):
        print("Erro na linkagem do shader:\n", glGetProgramInfoLog(Shader_programm, 512, None))

    glDeleteShader(vs)
    glDeleteShader(fs)

# -----------------------------
# Transformação de modelo
# -----------------------------

def transformacaoGenerica(Tx, Ty, Tz, Sx, Sy, Sz, Rx, Ry, Rz):
    # matriz de translação
    translacao = np.array([
        [1.0, 0.0, 0.0, Tx],
        [0.0, 1.0, 0.0, Ty],
        [0.0, 0.0, 1.0, Tz],
        [0.0, 0.0, 0.0, 1.0]], np.float32)

    # matriz de rotação em torno do eixo X
    angulo = np.radians(Rx)
    cos, sen = np.cos(angulo), np.sin(angulo)
    rotacaoX = np.array([
        [1.0, 0.0,  0.0, 0.0],
        [0.0, cos, -sen, 0.0],
        [0.0, sen,  cos, 0.0],
        [0.0, 0.0,  0.0, 1.0]
    ])

    # matriz de rotação em torno do eixo Y
    angulo = np.radians(Ry)
    cos, sen = np.cos(angulo), np.sin(angulo)
    rotacaoY = np.array([
        [ cos, 0.0, sen, 0.0],
        [ 0.0, 1.0, 0.0, 0.0],
        [-sen, 0.0, cos, 0.0],
        [ 0.0, 0.0, 0.0, 1.0]
    ])

    # matriz de rotação em torno do eixo Z
    angulo = np.radians(Rz)
    cos, sen = np.cos(angulo), np.sin(angulo)
    rotacaoZ = np.array([
        [cos, -sen, 0.0, 0.0],
        [sen,  cos, 0.0, 0.0],
        [0.0,  0.0, 1.0, 0.0],
        [0.0,  0.0, 0.0, 1.0]
    ])

    # combinação das 3 rotações
    rotacao = rotacaoZ.dot(rotacaoY.dot(rotacaoX))

    # matriz de escala
    escala = np.array([
        [Sx,  0.0, 0.0, 0.0],
        [0.0, Sy,  0.0, 0.0],
        [0.0, 0.0, Sz,  0.0],
        [0.0, 0.0, 0.0, 1.0]], np.float32)

    transformacaoFinal = translacao.dot(rotacao.dot(escala))

    # E passamos a matriz para o Vertex Shader.
    transformLoc = glGetUniformLocation(Shader_programm, "transform")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, transformacaoFinal)

# -----------------------------
# Câmeras: visualização e projeção
# -----------------------------

def montaMatrizView(pos, yaw, pitch):
    """
    Monta e retorna a matriz de visualização (lookAt manual) para uma câmera
    definida por posição, yaw e pitch. Usada tanto para a câmera de jogo
    quanto para a câmera de debug.

    Implementa um sistema de câmera no estilo FPS usando uma matriz lookAt manual.

    A ideia geral do lookAt é simular uma câmera no espaço 3D - ou seja, um ponto (posição da câmera)
    e uma direção (para onde ela está olhando). Em vez de mover a câmera diretamente,
    o que fazemos é aplicar a transformação inversa no mundo: deslocamos e rotacionamos
    tudo o que é desenhado, como se a câmera estivesse fixa na origem.

    Etapas principais:
      - A câmera tem posição (pos) e orientação (yaw/pitch):
        -> yaw controla a rotação horizontal (esquerda/direita),
        -> pitch controla a rotação vertical (cima/baixo).

      - A partir de yaw e pitch, calculamos o vetor 'front':
        ->é o vetor que aponta exatamente na direção para onde a câmera está olhando.
        ->Ele é normalizado para ter magnitude 1.

      - O vetor 'right' (ou 's') é obtido pelo produto vetorial entre 'front' e o eixo Y mundial (0,1,0):
        ->ele aponta para o lado direito da câmera e serve para calcular movimentos laterais (A/D).
        ->Esse vetor é sempre perpendicular ao 'front' e ao 'up' mundial.

      - O vetor 'up' (ou 'u') é recalculado como o produto vetorial entre 'right' e 'front':
        ->ele garante que o sistema de coordenadas da câmera forme uma base ortogonal
        (ou seja, os três vetores são perpendiculares entre si e normalizados).

    Montagem da matriz:
      - A matriz de visualização é formada colocando 'right', 'up' e '-front' nas três primeiras linhas:
            |  sx   sy   sz  -dot(s, pos) |
            |  ux   uy   uz  -dot(u, pos) |
            | -fx  -fy  -fz   dot(f, pos) |
            |   0    0    0       1       |
        Onde:
          s = right
          u = up
          f = front
        O termo -dot(...) representa a translação inversa da posição da câmera.

      - Essa matriz transforma o mundo para o referencial da câmera:
        ->o que está "na frente" da câmera é trazido para o eixo -Z,
        ->o "lado direito" para o +X e o "cima" para o +Y, como no sistema de visão padrão do OpenGL.

    Resultado:
      - O OpenGL renderiza como se a câmera estivesse sempre na origem (0,0,0),
        olhando para a direção (0,0,-1), e todo o resto do mundo se move ao redor dela.
    """
    front = np.array([
        np.cos(np.radians(yaw)) * np.cos(np.radians(pitch)),
        np.sin(np.radians(pitch)),
        np.sin(np.radians(yaw)) * np.cos(np.radians(pitch))
    ], dtype=np.float32)
    front = front / np.linalg.norm(front)

    center = pos + front
    up_mundo = np.array([0.0, 1.0, 0.0])

    f = (center - pos)
    f = f / np.linalg.norm(f)
    s = np.cross(f, up_mundo)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] = s
    view[1, :3] = u
    view[2, :3] = -f
    view[0, 3] = -np.dot(s, pos)
    view[1, 3] = -np.dot(u, pos)
    view[2, 3] =  np.dot(f, pos)

    return view

def especificaMatrizVisualizacao():
    # Usa a câmera de debug se a câmera de jogo estiver travada; senão usa a de jogo
    if Cam_jogo_travada:
        view = montaMatrizView(Cam_debug_pos, Cam_debug_yaw, Cam_debug_pitch)
    else:
        view = montaMatrizView(Cam_jogo_pos, Cam_jogo_yaw, Cam_jogo_pitch)

    transformLoc = glGetUniformLocation(Shader_programm, "view")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, view)

def especificaMatrizProjecao():
    # Especificação da matriz de projeção perspectiva.
    znear   = Cam_znear  # recorte z-near
    zfar    = Cam_zfar if not Cam_jogo_travada else 300.0  # câmera de debug enxerga mais longe
    fov     = np.radians(Cam_fov)  # campo de visão
    aspecto = WIDTH / HEIGHT        # aspecto

    a = 1 / (np.tan(fov / 2) * aspecto)
    b = 1 /  np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)
    projecao = np.array([
        [a,   0.0, 0.0,  0.0],
        [0.0, b,   0.0,  0.0],
        [0.0, 0.0, c,    d  ],
        [0.0, 0.0, -1.0, 1.0]
    ])

    transformLoc = glGetUniformLocation(Shader_programm, "proj")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, projecao)

def inicializaCamera():
    especificaMatrizVisualizacao()  # posição da câmera e orientação da câmera (rotação)
    especificaMatrizProjecao()       # perspectiva ou paralela

# -----------------------------
# Extração dos 6 planos do frustum (câmera de JOGO)
# -----------------------------
# Idêntico ao Exemplo 4, mas sempre usa os parâmetros da câmera de JOGO —
# mesmo quando a câmera de debug está ativa. O frustum que estamos visualizando
# e testando é sempre o da câmera de jogo.

def extraiPlanosFrustum():
    front = np.array([
        np.cos(np.radians(Cam_jogo_yaw)) * np.cos(np.radians(Cam_jogo_pitch)),
        np.sin(np.radians(Cam_jogo_pitch)),
        np.sin(np.radians(Cam_jogo_yaw)) * np.cos(np.radians(Cam_jogo_pitch))
    ], dtype=np.float32)
    front = front / np.linalg.norm(front)

    right = np.cross(front, np.array([0.0, 1.0, 0.0], dtype=np.float32))
    right = right / np.linalg.norm(right)

    up = np.cross(right, front)
    up = up / np.linalg.norm(up)

    fov_rad    = np.radians(Cam_fov)
    aspecto    = WIDTH / HEIGHT
    tang       = np.tan(fov_rad / 2)
    half_h_far = Cam_zfar * tang
    half_w_far = half_h_far * aspecto

    planos = []

    # Plano Near: posicionado à distância znear na direção 'front' a partir da câmera
    # Normal aponta para dentro (na direção que a câmera olha)
    planos.append((front.copy(), -np.dot(front, Cam_jogo_pos + front * Cam_znear)))

    # Plano Far: posicionado à distância zfar, normal aponta para trás (contra 'front')
    planos.append((-front.copy(), np.dot(front, Cam_jogo_pos + front * Cam_zfar)))

    # Planos Left e Right: inclinados pelo ângulo horizontal do FOV
    # Cada plano passa pela posição da câmera e aponta para dentro do frustum
    right_normal = np.cross(front * Cam_zfar - right * half_w_far, up)
    right_normal = right_normal / np.linalg.norm(right_normal)
    planos.append((right_normal.copy(), -np.dot(right_normal, Cam_jogo_pos)))

    left_normal = np.cross(up, front * Cam_zfar + right * half_w_far)
    left_normal = left_normal / np.linalg.norm(left_normal)
    planos.append((left_normal.copy(), -np.dot(left_normal, Cam_jogo_pos)))

    # Planos Top e Bottom: inclinados pelo ângulo vertical do FOV
    top_normal = np.cross(right, front * Cam_zfar - up * half_h_far)
    top_normal = top_normal / np.linalg.norm(top_normal)
    planos.append((top_normal.copy(), -np.dot(top_normal, Cam_jogo_pos)))

    bottom_normal = np.cross(front * Cam_zfar + up * half_h_far, right)
    bottom_normal = bottom_normal / np.linalg.norm(bottom_normal)
    planos.append((bottom_normal.copy(), -np.dot(bottom_normal, Cam_jogo_pos)))

    return planos

# -----------------------------
# Teste de visibilidade: bounding sphere vs frustum
# -----------------------------
# Para cada objeto, testamos sua bounding sphere contra os 6 planos do frustum.
#
# O teste para um plano (normal, d) é:
#     distancia = dot(normal, centro) + d
#
# Se distancia < -raio → a esfera está completamente do lado de fora desse plano
#                       → o objeto está fora do frustum → DESCARTA
#
# Se passar em todos os 6 planos → o objeto é potencialmente visível → DESENHA

def estaNoFrustum(centro, raio, planos):
    """
    Retorna True se a bounding sphere (centro, raio) está dentro (ou intersecta) o frustum.
    Retorna False se está completamente fora de pelo menos um plano.
    """
    for (normal, d) in planos:
        distancia = np.dot(normal, centro) + d
        if distancia < -raio:
            # Esfera completamente fora deste plano — descarta o objeto inteiro
            return False
    return True  # passou em todos os 6 planos — potencialmente visível

# -----------------------------
# Geração das posições dos objetos
# -----------------------------

def geraObjetos():
    global Objetos_posicoes

    rng = np.random.default_rng(42)  # seed fixa: mesma disposição independente do N
    Objetos_posicoes = [
        rng.uniform(-40.0, 40.0, size=3).astype(np.float32)
        for _ in range(Num_objetos)
    ]

# -----------------------------
# Entrada de teclado
# -----------------------------

def trataTeclado():
    """
    Movimenta a câmera no espaço 3D conforme teclas WASD.
    A direção do movimento segue o vetor 'front' (para onde o jogador está olhando),
    incluindo a inclinação vertical (pitch), assim o movimento é fiel ao olhar.
    Move a câmera ATIVA: câmera de jogo (modo normal) ou câmera de debug (modo travado).
    """
    global Cam_jogo_pos, Cam_debug_pos, Tempo_entre_frames

    velocidade = Cam_speed * Tempo_entre_frames

    # Seleciona os parâmetros da câmera ativa
    if not Cam_jogo_travada:
        yaw, pitch = Cam_jogo_yaw, Cam_jogo_pitch
    else:
        yaw, pitch = Cam_debug_yaw, Cam_debug_pitch

    frente = np.array([
        np.cos(np.radians(yaw)) * np.cos(np.radians(pitch)),
        np.sin(np.radians(pitch)),
        np.sin(np.radians(yaw)) * np.cos(np.radians(pitch))
    ], dtype=np.float32)
    frente /= np.linalg.norm(frente)

    direita = np.cross(frente, np.array([0.0, 1.0, 0.0]))
    direita /= np.linalg.norm(direita)

    # W/S: movem para frente/trás considerando o vetor de direção atual
    if glfw.get_key(Window, glfw.KEY_W) == glfw.PRESS:
        if not Cam_jogo_travada: Cam_jogo_pos  += frente * velocidade
        else:                    Cam_debug_pos += frente * velocidade
    if glfw.get_key(Window, glfw.KEY_S) == glfw.PRESS:
        if not Cam_jogo_travada: Cam_jogo_pos  -= frente * velocidade
        else:                    Cam_debug_pos -= frente * velocidade

    # A/D: movem lateralmente em relação à direção da câmera
    if glfw.get_key(Window, glfw.KEY_A) == glfw.PRESS:
        if not Cam_jogo_travada: Cam_jogo_pos  -= direita * velocidade
        else:                    Cam_debug_pos -= direita * velocidade
    if glfw.get_key(Window, glfw.KEY_D) == glfw.PRESS:
        if not Cam_jogo_travada: Cam_jogo_pos  += direita * velocidade
        else:                    Cam_debug_pos += direita * velocidade

    if glfw.get_key(Window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(Window, True)

# -----------------------------
# Definição de cor
# -----------------------------

def defineCor(r, g, b, a):
    # array de cores que vamos mandar pro shader
    cores = np.array([r, g, b, a])
    # buscou a localização na memória de video da variável corobjeto
    coresLoc = glGetUniformLocation(Shader_programm, "corobjeto")
    # passa os valores do vetor de cores aqui do python para o shader
    glUniform4fv(coresLoc, 1, cores)

# -----------------------------
# HUD no terminal
# -----------------------------

def atualizaHUD(fps):
    cam_str  = "DEBUG (jogo travada)" if Cam_jogo_travada else "JOGO "
    cull_str = "ON " if Frustum_culling_ativo else "OFF"
    print(
        f"\rCâm: [{cam_str}]  Culling: [{cull_str}]  "
        f"Cena: {Num_objetos:4d}  |  "
        f"Desenhados: {Objetos_desenhados:4d}  |  "
        f"Culled: {Objetos_culled:4d}  |  "
        f"FPS: {fps:6.1f}   ",
        end=""
    )

# -----------------------------
# Loop de renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames, Objetos_desenhados, Objetos_culled
    global _fps_acumulado, _fps_frames, _fps_timer

    tempo_anterior = glfw.get_time()
    _fps_timer     = tempo_anterior

    # Ativação do teste de profundidade. Sem ele, o OpenGL não sabe que faces devem ficar na frente e que faces devem ficar atrás.
    glEnable(GL_DEPTH_TEST)
    # Ativa mistura de cores, para podermos usar transparência (necessário para o vermelho semitransparente)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    print("\n--- Exemplo: Debug Visual do Frustum Culling ---")
    print("  T          — travar câmera de jogo e ativar câmera de debug")
    print("               (você sai da câmera de jogo e vê o frustum dela no mundo!)")
    print("  C          — alternar frustum culling (culled = vermelho / tudo azul)")
    print("  +/-        — mais/menos objetos")
    print("  W/A/S/D    — mover câmera ativa")
    print("  ESC        — fechar\n")
    print("  Fluxo sugerido:")
    print("    1. Olhe a cena normalmente (câmera de jogo livre)")
    print("    2. Pressione T para travar e ver o frustum amarelo no mundo")
    print("    3. Orbite com a câmera de debug para ver quais cubos estão fora")
    print("    4. Pressione C e veja os cubos culled ficarem vermelhos semitransparentes")

    while not glfw.window_should_close(Window):
        # calcula quantos segundos se passaram entre um frame e outro
        tempo_frame_atual  = glfw.get_time()
        Tempo_entre_frames = tempo_frame_atual - tempo_anterior
        tempo_anterior     = tempo_frame_atual

        glClearColor(0.15, 0.15, 0.2, 1.0)  # define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # limpa o buffer de cores e de profundidade
        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        # Extrai os planos do frustum da câmera de JOGO (independente de qual câmera está ativa)
        planos = extraiPlanosFrustum()

        # Atualiza o wireframe do frustum com a posição atual da câmera de jogo
        atualizaFrustumWireframe()

        # -----------------------------------------------
        # Passo 1: Desenha todos os cubos
        # -----------------------------------------------
        # Azul  → dentro do frustum (visível para a câmera de jogo)
        # Vermelho semitransparente → fora do frustum (culled — "raio-x" do que seria descartado)
        # Se culling desativado → todos azuis (o comportamento normal sem otimização)

        glBindVertexArray(Vao_cubo)

        Objetos_desenhados = 0
        Objetos_culled     = 0

        for pos in Objetos_posicoes:
            visivel = estaNoFrustum(pos, Bounding_raio, planos)

            if visivel:
                # Objeto dentro do frustum — desenha normalmente em azul
                defineCor(0.3, 0.6, 1.0, 1.0)
                transformacaoGenerica(pos[0], pos[1], pos[2], 1, 1, 1, 0, 0, 0)
                glDrawArrays(GL_TRIANGLES, 0, 36)
                Objetos_desenhados += 1
            else:
                Objetos_culled += 1
                if not Frustum_culling_ativo:
                    # Culling desativado: desenha mesmo assim em azul (comportamento sem otimização)
                    defineCor(0.3, 0.6, 1.0, 1.0)
                    transformacaoGenerica(pos[0], pos[1], pos[2], 1, 1, 1, 0, 0, 0)
                    glDrawArrays(GL_TRIANGLES, 0, 36)
                    Objetos_desenhados += 1
                else:
                    # Culling ativado: desenha em vermelho semitransparente (modo raio-x)
                    # O aluno vê o objeto que SERIA descartado — ele existe no mundo,
                    # mas a câmera de jogo não o vê e, portanto, não seria enviado à GPU
                    defineCor(1.0, 0.15, 0.15, 0.35)
                    transformacaoGenerica(pos[0], pos[1], pos[2], 1, 1, 1, 0, 0, 0)
                    glDrawArrays(GL_TRIANGLES, 0, 36)

        # -----------------------------------------------
        # Passo 2: Desenha o wireframe do frustum
        # -----------------------------------------------
        # Só faz sentido mostrar quando a câmera de debug está ativa —
        # com a câmera de jogo livre, o frustum coincide exatamente com o que
        # você está vendo, então não há "exterior" para observar.

        if Cam_jogo_travada:
            glBindVertexArray(Vao_frustum)
            # Usa a matriz identidade como transform (os vértices já estão em espaço do mundo)
            transformacaoGenerica(0, 0, 0, 1, 1, 1, 0, 0, 0)
            defineCor(1.0, 0.9, 0.0, 1.0)  # amarelo vibrante
            glLineWidth(2.0)               # linha mais espessa para visibilidade
            glDrawArrays(GL_LINES, 0, 24)  # 12 arestas × 2 vértices = 24 pontos
            glLineWidth(1.0)               # restaura espessura padrão

        glfw.poll_events()
        glfw.swap_buffers(Window)
        trataTeclado()

        # Acumula FPS para o HUD
        _fps_frames    += 1
        _fps_acumulado += (1.0 / Tempo_entre_frames) if Tempo_entre_frames > 0 else 0.0

        if tempo_frame_atual - _fps_timer >= 1.0:
            fps_medio      = _fps_acumulado / _fps_frames if _fps_frames > 0 else 0.0
            atualizaHUD(fps_medio)
            _fps_acumulado = 0.0
            _fps_frames    = 0
            _fps_timer     = tempo_frame_atual

    glfw.terminate()

# Função principal
def main():
    inicializaOpenGL()
    inicializaShaders()
    inicializaCubo()
    inicializaFrustumWireframe()
    geraObjetos()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()