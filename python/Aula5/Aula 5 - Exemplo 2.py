# Frustum Culling — exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra o conceito de Frustum Culling com Bounding Spheres:
# o descarte de objetos inteiros que estão fora do volume de visão da câmera (frustum),
# antes mesmo de enviá-los para a GPU.
#
# Conceitos demonstrados:
# - Frustum: o volume de visão da câmera, definido por 6 planos (Near, Far, Top, Bottom, Left, Right)
# - Bounding Sphere: uma esfera simples que envolve o objeto, usada como proxy para o teste
# - Frustum Culling: se a bounding sphere está completamente fora de qualquer plano do frustum,
#   o objeto é descartado na CPU — nenhuma draw call é emitida para a GPU
# - O Z-Buffer não poupa esse trabalho: sem culling, a GPU processa todos os objetos,
#   mesmo os completamente fora de campo
#
# Controles:
#   W/A/S/D     — mover câmera (FPS)
#   Mouse       — girar câmera
#   C           — alternar entre SEM frustum culling e COM frustum culling
#   +/-         — aumentar/diminuir número de objetos na cena
#   ESC         — fechar
#
# HUD no terminal (a cada ~1 segundo):
#   Modo, objetos na cena, objetos desenhados neste frame, draw calls, FPS

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np

Window          = None
Shader_programm = None
Vao_cubo        = None
WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0  # variavel utilizada para movimentar a camera

# Variáveis referentes a câmera virtual e sua projeção

Cam_speed  = 20.0  # velocidade da camera, 20 unidades por segundo
Cam_pos    = np.array([0.0, 0.0, 30.0])  # posicao inicial da câmera
Cam_yaw    = 180.0  # olhando para a cena
Cam_pitch  = 0.0    # controle vertical
lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# Projeção — guardamos os parâmetros globalmente para extrair os planos do frustum
# Os mesmos valores usados em especificaMatrizProjecao()
Cam_fov    = 67.0   # campo de visão em graus
Cam_znear  = 0.1    # plano de corte próximo
Cam_zfar   = 200.0  # plano de corte distante

# -----------------------------
# Estado da demonstração
# -----------------------------

# True  → frustum culling ativado (objetos fora de campo são descartados na CPU)
# False → sem culling (todos os objetos são enviados para a GPU)
Frustum_culling_ativo = False

# Número de objetos na cena
Num_objetos = 200

# Lista de posições dos objetos (gerada uma vez com seed fixa)
Objetos_posicoes = []  # lista de np.array([x, y, z])

# Raio do bounding volume de cada objeto (todos são cubos unitários, raio = sqrt(3)/2)
Bounding_raio = np.sqrt(3) / 2

# Contador de objetos desenhados no último frame (atualizado a cada frame)
Objetos_desenhados = 0

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
    global lastX, lastY, primeiro_mouse, Cam_yaw, Cam_pitch

    if primeiro_mouse:
        lastX, lastY   = xpos, ypos
        primeiro_mouse = False

    xoffset = xpos - lastX
    yoffset = lastY - ypos
    lastX, lastY = xpos, ypos

    sensibilidade = 0.1
    xoffset *= sensibilidade
    yoffset *= sensibilidade

    Cam_yaw   += xoffset
    Cam_pitch += yoffset

    Cam_pitch = max(-89.0, min(89.0, Cam_pitch))

def key_callback(window, key, scancode, action, mode):
    global Frustum_culling_ativo, Num_objetos

    if action != glfw.PRESS:
        return

    # C — alterna frustum culling
    if key == glfw.KEY_C:
        Frustum_culling_ativo = not Frustum_culling_ativo
        estado = "ATIVADO" if Frustum_culling_ativo else "DESATIVADO"
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
    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo Frustum Culling — CG em Tempo Real", None, None)
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
# Usamos o mesmo cubo do exemplo base.
# Cada cubo na cena é uma instância deste mesmo VAO, posicionado via uniform "transform".

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
# Geração das posições dos objetos
# -----------------------------
# Distribui N cubos aleatoriamente em um volume cúbico ao redor da origem.
# Seed fixa garante a mesma disposição sempre.

def geraObjetos():
    global Objetos_posicoes

    rng = np.random.default_rng(42)  # seed fixa: mesma disposição independente do N
    Objetos_posicoes = [
        rng.uniform(-40.0, 40.0, size=3).astype(np.float32)
        for _ in range(Num_objetos)
    ]

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
# Câmera (matriz de visualização)
# -----------------------------

def especificaMatrizVisualizacao():
    """
    Implementa um sistema de câmera no estilo FPS usando uma matriz lookAt manual.

    A ideia geral do lookAt é simular uma câmera no espaço 3D - ou seja, um ponto (posição da câmera)
    e uma direção (para onde ela está olhando). Em vez de mover a câmera diretamente,
    o que fazemos é aplicar a transformação inversa no mundo: deslocamos e rotacionamos
    tudo o que é desenhado, como se a câmera estivesse fixa na origem.

    Etapas principais:
      - A câmera tem posição (Cam_pos) e orientação (yaw/pitch):
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
            |  sx   sy   sz  -dot(s, Cam_pos) |
            |  ux   uy   uz  -dot(u, Cam_pos) |
            | -fx  -fy  -fz   dot(f, Cam_pos) |
            |   0    0    0         1         |
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
    global Cam_pos, Cam_yaw, Cam_pitch

    front = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    front = front / np.linalg.norm(front)

    center = Cam_pos + front
    up = np.array([0.0, 1.0, 0.0])

    f = (center - Cam_pos)
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] = s
    view[1, :3] = u
    view[2, :3] = -f
    view[0, 3] = -np.dot(s, Cam_pos)
    view[1, 3] = -np.dot(u, Cam_pos)
    view[2, 3] =  np.dot(f, Cam_pos)

    transformLoc = glGetUniformLocation(Shader_programm, "view")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, view)

# -----------------------------
# Projeção
# -----------------------------

def especificaMatrizProjecao():
    # Especificação da matriz de projeção perspectiva.
    znear   = Cam_znear  # recorte z-near
    zfar    = Cam_zfar   # recorte z-far
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
# Extração dos 6 planos do frustum
# -----------------------------
# O frustum é o volume piramidal truncado que a câmera enxerga.
# Ele é delimitado por 6 planos: Near, Far, Left, Right, Top, Bottom.
#
# Estratégia: construímos os planos diretamente no espaço do mundo a partir
# dos vetores da câmera (front, right, up) e dos parâmetros de projeção.
#
# Cada plano é representado por um vetor normal (nx, ny, nz) e uma distância d,
# de forma que o semiespaço "dentro" do frustum satisfaz:
#
#     dot(normal, ponto) + d >= 0
#
# Se essa equação for negativa para QUALQUER um dos 6 planos, o ponto está fora.

def extraiPlanosFrustum():
    """
    Retorna os 6 planos do frustum como lista de (normal, d).
    Construídos analiticamente a partir dos parâmetros da câmera e projeção.
    """
    # Recalcula os vetores da câmera (mesma lógica de especificaMatrizVisualizacao)
    front = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    front = front / np.linalg.norm(front)

    right = np.cross(front, np.array([0.0, 1.0, 0.0]))
    right = right / np.linalg.norm(right)

    up = np.cross(right, front)
    up = up / np.linalg.norm(up)

    fov_rad = np.radians(Cam_fov)
    aspecto = WIDTH / HEIGHT

    # Metade da altura e largura do frustum no plano far (para calcular planos laterais)
    tang      = np.tan(fov_rad / 2)
    half_h_far = Cam_zfar  * tang             # meia-altura no far plane
    half_w_far = half_h_far * aspecto          # meia-largura no far plane

    # Os planos são construídos com suas normais apontando para DENTRO do frustum.
    # Isso permite testar: dot(normal, centro) + d >= -raio → objeto potencialmente visível.

    planos = []

    # Plano Near: posicionado à distância znear na direção 'front' a partir da câmera
    # Normal aponta para dentro (na direção da câmera olha)
    planos.append((front.copy(), -np.dot(front, Cam_pos + front * Cam_znear)))

    # Plano Far: posicionado à distância zfar, normal aponta para trás (contra 'front')
    planos.append((-front.copy(), np.dot(front, Cam_pos + front * Cam_zfar)))

    # Planos Left e Right: inclinados pelo ângulo horizontal do FOV
    # Cada plano passa pela posição da câmera e aponta para dentro do frustum
    right_normal = np.cross(front * Cam_zfar - right * half_w_far, up)
    right_normal = right_normal / np.linalg.norm(right_normal)
    planos.append((right_normal.copy(), -np.dot(right_normal, Cam_pos)))

    left_normal = np.cross(up, front * Cam_zfar + right * half_w_far)
    left_normal = left_normal / np.linalg.norm(left_normal)
    planos.append((left_normal.copy(), -np.dot(left_normal, Cam_pos)))

    # Planos Top e Bottom: inclinados pelo ângulo vertical do FOV
    top_normal = np.cross(right, front * Cam_zfar - up * half_h_far)
    top_normal = top_normal / np.linalg.norm(top_normal)
    planos.append((top_normal.copy(), -np.dot(top_normal, Cam_pos)))

    bottom_normal = np.cross(front * Cam_zfar + up * half_h_far, right)
    bottom_normal = bottom_normal / np.linalg.norm(bottom_normal)
    planos.append((bottom_normal.copy(), -np.dot(bottom_normal, Cam_pos)))

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
#
# Este é o teste conservador (PVS): pode incluir alguns objetos que o Z-Buffer
# depois descartará, mas nunca exclui objetos visíveis.

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
# Entrada de teclado
# -----------------------------

def trataTeclado():
    """
    Movimenta a câmera no espaço 3D conforme teclas WASD.
    A direção do movimento segue o vetor 'front' (para onde o jogador está olhando),
    incluindo a inclinação vertical (pitch), assim o movimento é fiel ao olhar.
    """
    global Cam_pos, Cam_yaw, Cam_pitch, Tempo_entre_frames

    velocidade = Cam_speed * Tempo_entre_frames

    frente = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    frente /= np.linalg.norm(frente)

    direita = np.cross(frente, np.array([0.0, 1.0, 0.0]))
    direita /= np.linalg.norm(direita)

    # W/S: movem para frente/trás considerando o vetor de direção atual
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
    modo_str = "COM frustum culling" if Frustum_culling_ativo else "SEM frustum culling"
    print(
        f"\r[{modo_str}]  "
        f"Objetos na cena: {Num_objetos:4d}  |  "
        f"Desenhados: {Objetos_desenhados:4d}  |  "
        f"Draw calls: {Objetos_desenhados:4d}  |  "
        f"FPS: {fps:6.1f}   ",
        end=""
    )

# -----------------------------
# Loop de renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames, Objetos_desenhados
    global _fps_acumulado, _fps_frames, _fps_timer

    tempo_anterior = glfw.get_time()
    _fps_timer     = tempo_anterior

    # Ativação do teste de profundidade. Sem ele, o OpenGL não sabe que faces devem ficar na frente e que faces devem ficar atrás.
    glEnable(GL_DEPTH_TEST)
    # Ativa mistura de cores, para podermos usar transparência
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    print("\n--- Exemplo: Frustum Culling ---")
    print("  C      — alternar frustum culling (SEM / COM)")
    print("  +/-    — mais/menos objetos na cena")
    print("  W/A/S/D + mouse — câmera FPS")
    print("  ESC    — fechar\n")
    print("  Dica: ative o culling (C) e gire a câmera para ver os draw calls caírem!")

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

        glBindVertexArray(Vao_cubo)

        # Extrai os 6 planos do frustum uma vez por frame (custo fixo, independente de N)
        planos = extraiPlanosFrustum() if Frustum_culling_ativo else None

        Objetos_desenhados = 0

        for pos in Objetos_posicoes:
            # --- Teste de visibilidade na CPU ---
            # Com culling ativo: testamos a bounding sphere antes de qualquer draw call.
            # Se o objeto estiver fora do frustum, pulamos completamente — zero custo na GPU.
            # Sem culling: enviamos todos os objetos para a GPU, que processa tudo
            # (mesmo o que o Z-Buffer vai descartar no final).
            if Frustum_culling_ativo and not estaNoFrustum(pos, Bounding_raio, planos):
                continue  # objeto fora do frustum — sem draw call, sem custo de GPU

            # Objeto visível (ou culling desativado) — emite a draw call
            defineCor(0.3, 0.6, 1.0, 1.0)
            transformacaoGenerica(pos[0], pos[1], pos[2], 1, 1, 1, 0, 0, 0)
            glDrawArrays(GL_TRIANGLES, 0, 36)
            Objetos_desenhados += 1

        glfw.poll_events()
        glfw.swap_buffers(Window)
        trataTeclado()

        # Acumula FPS para o HUD
        _fps_frames     += 1
        _fps_acumulado  += (1.0 / Tempo_entre_frames) if Tempo_entre_frames > 0 else 0.0

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
    geraObjetos()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()