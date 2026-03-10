# Malha Interativa — exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra os conceitos fundamentais de modelagem geométrica:
# vértices, faces, triângulos e o impacto da resolução da malha na forma do objeto.
#
# Três objetos são exibidos lado a lado:
#   - Cubo     (esquerda):  sempre 12 triângulos — faces planas, resolução não muda
#   - Pirâmide (centro):    sempre 6 triângulos  — faces planas, resolução não muda
#   - Esfera   (direita):   resolução variável   — mais triângulos = forma mais suave
#
# A comparação entre os três objetos deixa claro que:
#   * Formas planas não ganham nada com mais triângulos
#   * Formas curvas dependem de triângulos para aproximar a superfície
#   * A malha é sempre uma "casca", não um volume sólido
#
# O shader usa uma luz direcional fixa e hardcoded para sombrear as faces
# com base nas normais — isso não é conteúdo desta aula, é apenas um recurso
# visual para tornar a forma 3D legível. O foco é a malha, não a iluminação.
#
# Controles:
#   W/A/S/D     — mover câmera (FPS)
#   Mouse       — girar câmera
#   +/-         — aumentar/diminuir resolução da esfera (4 a 64 subdivisões)
#   F           — wireframe on/off
#   ESC         — fechar
#
# HUD no terminal (a cada ~1 segundo):
#   Resolução da esfera, triângulos por objeto, total de triângulos, FPS

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np

Window          = None
Shader_programm = None

# Um VAO por objeto — cada um tem sua própria geometria
Vao_cubo     = None
Vao_piramide = None
Vao_esfera   = None

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0  # variavel utilizada para movimentar a camera

# Variáveis referentes a câmera virtual e sua projeção

Cam_speed  = 8.0  # velocidade da camera, 8 unidades por segundo
Cam_pos    = np.array([0.0, 0.5, 7.0])  # posicao inicial da câmera
Cam_yaw   = -90.0  # Aponta para o fundo da cena (eixo -Z)
Cam_pitch = -4.0 # Inclina levemente para baixo para focar a base
lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# -----------------------------
# Estado da demonstração
# -----------------------------

# Resolução da esfera: número de subdivisões (rings = sectors = Resolucao_esfera)
# Valores baixos (4) → poucas faces, forma poligonal visível
# Valores altos (64) → muitas faces, aparência suave e arredondada
Resolucao_esfera = 8

# Triângulos de cada objeto (atualizados ao reconstruir as malhas)
Tri_cubo     = 0
Tri_piramide = 0
Tri_esfera   = 0

# Wireframe
Wireframe = False

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
    global Resolucao_esfera, Wireframe

    if action != glfw.PRESS:
        return

    # + — mais subdivisões na esfera (mais triângulos, forma mais suave)
    if key in (glfw.KEY_EQUAL, glfw.KEY_KP_ADD):
        Resolucao_esfera = min(Resolucao_esfera + 2, 64)
        inicializaEsfera()
        print(f"\n[ESFERA] Resolução: {Resolucao_esfera}x{Resolucao_esfera} → {Tri_esfera} triângulos")

    # - — menos subdivisões na esfera (menos triângulos, forma mais angular)
    if key in (glfw.KEY_MINUS, glfw.KEY_KP_SUBTRACT):
        Resolucao_esfera = max(Resolucao_esfera - 2, 4)
        inicializaEsfera()
        print(f"\n[ESFERA] Resolução: {Resolucao_esfera}x{Resolucao_esfera} → {Tri_esfera} triângulos")

    # F — alterna wireframe
    if key == glfw.KEY_F:
        Wireframe = not Wireframe
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if Wireframe else GL_FILL)
        print(f"\n[WIRE] Wireframe {'ON' if Wireframe else 'OFF'}")

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    # Inicializa GLFW
    glfw.init()

    # Criação de uma janela
    Window = glfw.create_window(WIDTH, HEIGHT, "Malha Interativa — CG em Tempo Real", None, None)
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
# Inicialização das geometrias
# -----------------------------
# Cada objeto é construído como uma lista plana de vértices + normais.
# Formato por vértice: [x, y, z, nx, ny, nz]
# A normal de cada face é calculada manualmente e replicada para os 3 vértices
# do triângulo — isso produz o efeito "facetado" (normal de face).
#
# O cubo e a pirâmide têm geometria fixa (faces planas = normais triviais).
# A esfera é reconstruída dinamicamente ao mudar a resolução.

def calculaNormal(v0, v1, v2):
    """
    Calcula a normal de face de um triângulo definido por três vértices.
    A normal é o produto vetorial das duas arestas, normalizado.
    Ela indica para qual lado a superfície está "olhando" — base da iluminação.
    """
    a = v1 - v0
    b = v2 - v0
    n = np.cross(a, b)
    norma = np.linalg.norm(n)
    if norma < 1e-8:
        return np.array([0.0, 1.0, 0.0])  # fallback: normal para cima
    return n / norma

def montaVAO(dados):
    """
    Cria e retorna um VAO a partir de um array numpy de vértices com normais.
    Formato esperado: [x, y, z, nx, ny, nz, x, y, z, nx, ny, nz, ...]
    """
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, dados, GL_STATIC_DRAW)

    stride = 6 * 4  # 6 floats × 4 bytes por float

    # Atributo 0: posição (x, y, z)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)

    # Atributo 1: normal (nx, ny, nz) — usada pelo shader para sombrear
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

    return vao

def inicializaCubo():
    """
    Constrói um cubo unitário centrado na origem.
    O cubo tem sempre 12 triângulos (2 por face × 6 faces).
    Independentemente de resolução, um cubo não muda — faces planas não precisam
    de subdivisão para parecer corretas.
    """
    global Vao_cubo, Tri_cubo

    # Definição das 6 faces do cubo, cada uma com 4 vértices e 1 normal fixa
    # Cada face é dividida em 2 triângulos (total: 12 triângulos)
    faces = [
        # (4 vértices da face, normal da face)
        # Frente (+Z)
        ([[-0.5,-0.5, 0.5],[ 0.5,-0.5, 0.5],[ 0.5, 0.5, 0.5],[-0.5, 0.5, 0.5]], [ 0, 0, 1]),
        # Trás (-Z)
        ([[ 0.5,-0.5,-0.5],[-0.5,-0.5,-0.5],[-0.5, 0.5,-0.5],[ 0.5, 0.5,-0.5]], [ 0, 0,-1]),
        # Direita (+X)
        ([[ 0.5,-0.5, 0.5],[ 0.5,-0.5,-0.5],[ 0.5, 0.5,-0.5],[ 0.5, 0.5, 0.5]], [ 1, 0, 0]),
        # Esquerda (-X)
        ([[-0.5,-0.5,-0.5],[-0.5,-0.5, 0.5],[-0.5, 0.5, 0.5],[-0.5, 0.5,-0.5]], [-1, 0, 0]),
        # Cima (+Y)
        ([[-0.5, 0.5, 0.5],[ 0.5, 0.5, 0.5],[ 0.5, 0.5,-0.5],[-0.5, 0.5,-0.5]], [ 0, 1, 0]),
        # Baixo (-Y)
        ([[-0.5,-0.5,-0.5],[ 0.5,-0.5,-0.5],[ 0.5,-0.5, 0.5],[-0.5,-0.5, 0.5]], [ 0,-1, 0]),
    ]

    dados = []
    for verts, normal in faces:
        v = [np.array(v, dtype=np.float32) for v in verts]
        n = np.array(normal, dtype=np.float32)
        # Triângulo 1: v0, v1, v2
        for vi in [v[0], v[1], v[2]]:
            dados.extend(vi); dados.extend(n)
        # Triângulo 2: v0, v2, v3
        for vi in [v[0], v[2], v[3]]:
            dados.extend(vi); dados.extend(n)

    dados = np.array(dados, dtype=np.float32)
    Tri_cubo = len(dados) // 18  # 18 floats por triângulo (3 vértices × 6 floats)
    Vao_cubo = montaVAO(dados)

def inicializaPiramide():
    """
    Constrói uma pirâmide de base quadrada centrada na origem.
    4 faces triangulares laterais + 2 triângulos de base = 6 triângulos no total.
    Assim como o cubo, a pirâmide tem geometria fixa — faces planas não mudam
    com resolução.
    """
    global Vao_piramide, Tri_piramide

    # Vértices da pirâmide
    topo  = np.array([ 0.0,  0.8,  0.0], dtype=np.float32)
    ffd   = np.array([-0.5, -0.4,  0.5], dtype=np.float32)  # frente-direita
    ffe   = np.array([ 0.5, -0.4,  0.5], dtype=np.float32)  # frente-esquerda
    tfd   = np.array([-0.5, -0.4, -0.5], dtype=np.float32)  # trás-direita
    tfe   = np.array([ 0.5, -0.4, -0.5], dtype=np.float32)  # trás-esquerda

    # Triângulos da pirâmide: cada tupla é (v0, v1, v2)
    triangulos = [
        (topo, ffd, ffe),   # face frontal
        (topo, ffe, tfe),   # face direita
        (topo, tfe, tfd),   # face traseira
        (topo, tfd, ffd),   # face esquerda
        (ffd,  tfd, tfe),   # base triângulo 1
        (ffd,  tfe, ffe),   # base triângulo 2
    ]

    dados = []
    for v0, v1, v2 in triangulos:
        n = calculaNormal(v0, v1, v2)
        for vi in [v0, v1, v2]:
            dados.extend(vi); dados.extend(n)

    dados = np.array(dados, dtype=np.float32)
    Tri_piramide = len(dados) // 18
    Vao_piramide = montaVAO(dados)

def inicializaEsfera():
    """
    Constrói uma esfera UV com Resolucao_esfera × Resolucao_esfera subdivisões.

    Diferentemente do cubo e da pirâmide, a esfera é uma forma CURVA.
    Uma superfície curva não pode ser representada exatamente com triângulos planos —
    ela é sempre uma APROXIMAÇÃO. Quanto mais triângulos, melhor a aproximação:
      - Resolução  4 →   32 triângulos → formato quase octaédrico
      - Resolução  8 →  128 triângulos → formato levemente arredondado
      - Resolução 16 →  512 triângulos → formato bem suave
      - Resolução 32 → 2048 triângulos → quase indistinguível de uma esfera real

    Cada célula da grade UV gera 2 triângulos. A normal de cada triângulo é
    calculada pelo produto vetorial das arestas (normal de face = efeito facetado).
    """
    global Vao_esfera, Tri_esfera

    rings   = Resolucao_esfera
    sectors = Resolucao_esfera
    raio    = 0.8

    dados = []
    for r in range(rings):
        for s in range(sectors):
            theta0 = np.pi *  r      / rings
            theta1 = np.pi * (r + 1) / rings
            phi0   = 2 * np.pi *  s      / sectors
            phi1   = 2 * np.pi * (s + 1) / sectors

            # Quatro vértices da célula da grade esférica
            v00 = np.array([np.sin(theta0)*np.cos(phi0), np.cos(theta0), np.sin(theta0)*np.sin(phi0)], np.float32) * raio
            v01 = np.array([np.sin(theta0)*np.cos(phi1), np.cos(theta0), np.sin(theta0)*np.sin(phi1)], np.float32) * raio
            v10 = np.array([np.sin(theta1)*np.cos(phi0), np.cos(theta1), np.sin(theta1)*np.sin(phi0)], np.float32) * raio
            v11 = np.array([np.sin(theta1)*np.cos(phi1), np.cos(theta1), np.sin(theta1)*np.sin(phi1)], np.float32) * raio

            # Triângulo 1 — normal de face calculada pelos seus próprios vértices
            n1 = calculaNormal(v00, v10, v11)
            for vi in [v00, v10, v11]:
                dados.extend(vi); dados.extend(n1)

            # Triângulo 2 — normal de face calculada pelos seus próprios vértices
            n2 = calculaNormal(v00, v11, v01)
            for vi in [v00, v11, v01]:
                dados.extend(vi); dados.extend(n2)

    dados = np.array(dados, dtype=np.float32)
    Tri_esfera = len(dados) // 18
    Vao_esfera = montaVAO(dados)

# -----------------------------
# Shaders
# -----------------------------
# O vertex shader recebe posição E normal, e passa a normal para o fragment shader.
# O fragment shader aplica uma iluminação direcional simples cuja direção é enviada
# como uniform (luz_dir) a cada frame — a luz orbita a cena automaticamente.
# Isso é apenas um recurso visual para tornar a forma 3D legível.
# O foco desta aula é a malha, não o modelo de iluminação.
#
# A fórmula usada é:
#   intensidade = max(dot(normal_mundo, luz_dir), 0.0) * 0.8 + 0.2
# O "+0.2" é a luz ambiente — garante que faces de costas para a luz não ficam
# completamente pretas (o que dificultaria ver a geometria).

def inicializaShaders():
    global Shader_programm

    # Especificação do Vertex Shader:
    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        layout(location = 1) in vec3 vertex_normal;
        //view - matriz da câmera recebida do PYTHON
        //proj - matriz de projeção recebida do PYTHON
        //transform - matriz de transformação geométrica do objeto recebida do PYTHON
        uniform mat4 transform, view, proj;
        out vec3 normal_mundo;
        void main () {
            gl_Position   = proj * view * transform * vec4(vertex_posicao, 1.0);
            // Transforma a normal para o espaço do mundo usando apenas a parte
            // rotação/escala da matriz de transformação (ignora translação)
            normal_mundo  = mat3(transform) * vertex_normal;
        }
    """
    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    if not glGetShaderiv(vs, GL_COMPILE_STATUS):
        print("Erro no vertex shader:\n", glGetShaderInfoLog(vs, 512, None))

    # Especificação do Fragment Shader:
    fragment_shader = """
        #version 400
        in  vec3 normal_mundo;
        out vec4 frag_colour;
        uniform vec4 corobjeto;
        uniform vec3 luz_dir;  // direção da luz orbital — atualizada pelo Python a cada frame

        void main () {
            // Direção da luz direcional — recebida do Python como uniform,
            // atualizada a cada frame para orbitar a cena automaticamente.
            // Isso NÃO é o conteúdo desta aula: é apenas um truque visual
            // para dar volume aos objetos e tornar a malha legível em 3D.
            vec3  n           = normalize(normal_mundo);
            float difuso      = max(dot(n, luz_dir), 0.0) * 0.8;
            float ambiente    = 0.2;  // luz mínima para faces de costas não ficarem pretas
            float intensidade = difuso + ambiente;
            frag_colour = vec4(corobjeto.rgb * intensidade, corobjeto.a);
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
    znear   = 0.1    # recorte z-near
    zfar    = 100.0  # recorte z-far
    fov     = np.radians(67.0)  # campo de visão
    aspecto = WIDTH / HEIGHT     # aspecto

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
    total = Tri_cubo + Tri_piramide + Tri_esfera
    print(
        f"\r[Res. esfera: {Resolucao_esfera:2d}x{Resolucao_esfera:<2d}]  "
        f"Cubo: {Tri_cubo:4d} tri  |  "
        f"Pirâmide: {Tri_piramide:4d} tri  |  "
        f"Esfera: {Tri_esfera:4d} tri  |  "
        f"Total: {total:5d} tri  |  "
        f"FPS: {fps:6.1f}   ",
        end=""
    )

# -----------------------------
# Loop de renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames, _fps_acumulado, _fps_frames, _fps_timer

    tempo_anterior = glfw.get_time()
    _fps_timer     = tempo_anterior

    # Ativação do teste de profundidade. Sem ele, o OpenGL não sabe que faces devem ficar na frente e que faces devem ficar atrás.
    glEnable(GL_DEPTH_TEST)
    # Ativa mistura de cores, para podermos usar transparência
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    print("\n--- Exemplo: Malha Interativa ---")
    print("  +/-    — aumentar/diminuir resolução da esfera")
    print("  F      — wireframe on/off (veja a malha!)")
    print("  W/A/S/D + mouse — câmera FPS")
    print("  ESC    — fechar\n")
    print("  Observe: o cubo e a pirâmide não mudam com +/- — faces planas não precisam")
    print("  de subdivisão. Apenas a esfera (forma curva) precisa de mais triângulos")
    print("  para parecer arredondada.\n")
    print("  Nota: a variação de brilho entre faces é apenas um recurso visual para")
    print("  tornar a geometria 3D legível. A luz orbita automaticamente a cena.")
    print("  Iluminação será vista em detalhes em outra aula.\n")

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

        # Calcula a direção da luz orbital: gira em torno do eixo Y com o tempo.
        # A altura Y é fixa (0.6) para manter um ângulo de incidência interessante.
        # Isso NÃO é conteúdo desta aula — apenas anima a luz para dar volume.
        angulo_luz = tempo_frame_atual * 0.8  # 0.8 rad/s — rotação suave
        luz_x = np.cos(angulo_luz)
        luz_z = np.sin(angulo_luz)
        luz_dir = np.array([luz_x, 0.6, luz_z], dtype=np.float32)
        luz_dir /= np.linalg.norm(luz_dir)
        luzLoc = glGetUniformLocation(Shader_programm, "luz_dir")
        glUniform3fv(luzLoc, 1, luz_dir)

        # --- Cubo (esquerda) — azul ---
        glBindVertexArray(Vao_cubo)
        defineCor(0.3, 0.6, 1.0, 1.0)
        transformacaoGenerica(-2.5, 0, 0,  1, 1, 1,  20, 30, 0)
        glDrawArrays(GL_TRIANGLES, 0, Tri_cubo * 3)

        # --- Pirâmide (centro) — laranja ---
        glBindVertexArray(Vao_piramide)
        defineCor(1.0, 0.6, 0.2, 1.0)
        transformacaoGenerica(0, 0, 0,  1, 1, 1,  0, 20, 0)
        glDrawArrays(GL_TRIANGLES, 0, Tri_piramide * 3)

        # --- Esfera (direita) — verde ---
        glBindVertexArray(Vao_esfera)
        defineCor(0.3, 0.9, 0.5, 1.0)
        transformacaoGenerica(2.5, 0, 0,  1, 1, 1,  0, 0, 0)
        glDrawArrays(GL_TRIANGLES, 0, Tri_esfera * 3)

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
    inicializaPiramide()
    inicializaEsfera()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()