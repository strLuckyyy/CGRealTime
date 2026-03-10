# Normais de Face vs. Normais de Vértice — exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra a diferença visual entre dois tipos de normais geométricas:
#
#   Normal de Face:
#     - Um único vetor normal por triângulo, perpendicular ao plano da face
#     - Todos os vértices do triângulo compartilham a mesma normal
#     - Resultado visual: aparência FACETADA — cada face tem brilho uniforme e distinto
#     - O limite entre triângulos adjacentes é visível
#
#   Normal de Vértice:
#     - Cada vértice recebe a média das normais das faces ao redor
#     - A normal é INTERPOLADA pelo rasterizador entre os vértices do triângulo
#     - Resultado visual: aparência SUAVE — transição gradual de brilho entre faces
#     - Os limites entre triângulos desaparecem visualmente
#
# Os mesmos três objetos do Exemplo 1 são usados lado a lado.
# A tecla N alterna entre os dois modos em todos simultaneamente.
# Com a esfera em baixa resolução, o efeito é especialmente dramático:
# a forma claramente poligonal se torna visualmente "redonda" apenas trocando as normais.
#
# O shader usa iluminação direcional simples com direção fixa hardcoded —
# isso não é conteúdo desta aula, é apenas um recurso visual para que as normais
# produzam diferença perceptível na tela. O foco é a normal, não o modelo de luz.
#
# Controles:
#   W/A/S/D     — mover câmera (FPS)
#   Mouse       — girar câmera
#   N           — alternar entre Normal de Face e Normal de Vértice
#   +/-         — aumentar/diminuir resolução da esfera
#   F           — wireframe on/off
#   ESC         — fechar
#
# HUD no terminal (a cada ~1 segundo):
#   Modo de normal ativo, resolução da esfera, triângulos totais, FPS

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import ctypes

Window          = None
Shader_programm = None

# Um VAO por objeto por modo — cada combinação (objeto × modo_normal) tem seu próprio VAO
# pois a diferença entre os modos está nos dados do VBO (as normais), não nos shaders
Vao_cubo_face     = None  # cubo com normais de face
Vao_cubo_vertice  = None  # cubo com normais de vértice
Vao_pir_face      = None  # pirâmide com normais de face
Vao_pir_vertice   = None  # pirâmide com normais de vértice
Vao_esf_face      = None  # esfera com normais de face
Vao_esf_vertice   = None  # esfera com normais de vértice

WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0  # variavel utilizada para movimentar a camera

# Variáveis referentes a câmera virtual e sua projeção

Cam_speed = 8.0  # velocidade da camera, 8 unidades por segundo
Cam_pos   = np.array([0.0, 0.5, 7.0])  # posicao inicial da câmera
Cam_yaw   = -90.0  # Aponta para o fundo da cena (eixo -Z)
Cam_pitch = -4.0 # Inclina levemente para baixo para focar a base
lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# -----------------------------
# Estado da demonstração
# -----------------------------

# False → Normal de Face  (aparência facetada, cada triângulo com brilho uniforme)
# True  → Normal de Vértice (aparência suave, brilho interpolado entre vértices)
Modo_normal_vertice = False

# Resolução da esfera
Resolucao_esfera = 8

# Contadores de triângulos
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
    global Modo_normal_vertice, Resolucao_esfera, Wireframe

    if action != glfw.PRESS:
        return

    # N — alterna entre normal de face e normal de vértice
    if key == glfw.KEY_N:
        Modo_normal_vertice = not Modo_normal_vertice
        modo_str = "VÉRTICE (suave)" if Modo_normal_vertice else "FACE (facetada)"
        print(f"\n[NORMAL] Modo: {modo_str}")

    # + — mais subdivisões na esfera
    if key in (glfw.KEY_EQUAL, glfw.KEY_KP_ADD):
        Resolucao_esfera = min(Resolucao_esfera + 2, 64)
        inicializaEsfera()
        print(f"\n[ESFERA] Resolução: {Resolucao_esfera}x{Resolucao_esfera} → {Tri_esfera} triângulos")

    # - — menos subdivisões na esfera
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
    Window = glfw.create_window(WIDTH, HEIGHT, "Normal de Face vs. Vértice — CG em Tempo Real", None, None)
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
# Utilitários de geometria
# -----------------------------

def calculaNormal(v0, v1, v2):
    """
    Calcula a normal de face de um triângulo definido por três vértices.
    A normal é o produto vetorial das duas arestas, normalizado.
    """
    a = v1 - v0
    b = v2 - v0
    n = np.cross(a, b)
    norma = np.linalg.norm(n)
    if norma < 1e-8:
        return np.array([0.0, 1.0, 0.0])
    return n / norma

def montaVAO(dados):
    """
    Cria e retorna um VAO a partir de um array numpy de vértices com normais.
    Formato: [x, y, z, nx, ny, nz, ...]
    """
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, dados, GL_STATIC_DRAW)

    stride = 6 * 4  # 6 floats × 4 bytes

    # Atributo 0: posição (x, y, z)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, None)

    # Atributo 1: normal (nx, ny, nz)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

    return vao

# -----------------------------
# Cubo: normais de face e de vértice
# -----------------------------

def inicializaCubo():
    """
    Constrói o cubo em dois VAOs: um com normais de face, outro com normais de vértice.

    Normal de face:
      Todos os 3 vértices de cada triângulo recebem a mesma normal — perpendicular
      ao plano da face. Cada face do cubo tem brilho uniforme e distinto das vizinhas.
      O resultado é a aparência "blocosa" característica.

    Normal de vértice:
      Cada vértice do cubo é compartilhado por 3 faces. Sua normal de vértice é a
      média das normais dessas 3 faces, normalizada. O rasterizador interpola essa
      normal entre os vértices, criando uma transição suave de brilho.
      No cubo, o efeito é mais sutil — os cantos ficam levemente "arredondados" visualmente.
    """
    global Vao_cubo_face, Vao_cubo_vertice, Tri_cubo

    faces = [
        ([[-0.5,-0.5, 0.5],[ 0.5,-0.5, 0.5],[ 0.5, 0.5, 0.5],[-0.5, 0.5, 0.5]], [ 0, 0, 1]),
        ([[ 0.5,-0.5,-0.5],[-0.5,-0.5,-0.5],[-0.5, 0.5,-0.5],[ 0.5, 0.5,-0.5]], [ 0, 0,-1]),
        ([[ 0.5,-0.5, 0.5],[ 0.5,-0.5,-0.5],[ 0.5, 0.5,-0.5],[ 0.5, 0.5, 0.5]], [ 1, 0, 0]),
        ([[-0.5,-0.5,-0.5],[-0.5,-0.5, 0.5],[-0.5, 0.5, 0.5],[-0.5, 0.5,-0.5]], [-1, 0, 0]),
        ([[-0.5, 0.5, 0.5],[ 0.5, 0.5, 0.5],[ 0.5, 0.5,-0.5],[-0.5, 0.5,-0.5]], [ 0, 1, 0]),
        ([[-0.5,-0.5,-0.5],[ 0.5,-0.5,-0.5],[ 0.5,-0.5, 0.5],[-0.5,-0.5, 0.5]], [ 0,-1, 0]),
    ]

    # --- VAO com normais de FACE ---
    dados_face = []
    for verts, normal in faces:
        v = [np.array(x, dtype=np.float32) for x in verts]
        n = np.array(normal, dtype=np.float32)
        for vi in [v[0], v[1], v[2]]: dados_face.extend(vi); dados_face.extend(n)
        for vi in [v[0], v[2], v[3]]: dados_face.extend(vi); dados_face.extend(n)
    dados_face = np.array(dados_face, dtype=np.float32)
    Tri_cubo = len(dados_face) // 18
    Vao_cubo_face = montaVAO(dados_face)

    # --- VAO com normais de VÉRTICE ---
    # Para cada um dos 8 vértices únicos do cubo, acumulamos as normais das faces
    # às quais ele pertence e fazemos a média.
    # Cada vértice de um cubo pertence a exatamente 3 faces → média de 3 normais.

    # Mapeamento: posição do vértice → lista de normais das faces que o contêm
    normais_por_vertice = {}
    for verts, normal in faces:
        n = np.array(normal, dtype=np.float32)
        for v in verts:
            chave = tuple(np.round(v, 5))
            if chave not in normais_por_vertice:
                normais_por_vertice[chave] = []
            normais_por_vertice[chave].append(n)

    def normal_vertice(v):
        chave = tuple(np.round(v, 5))
        ns = normais_por_vertice[chave]
        media = np.mean(ns, axis=0)
        return media / np.linalg.norm(media)

    dados_vert = []
    for verts, _ in faces:
        v = [np.array(x, dtype=np.float32) for x in verts]
        for vi in [v[0], v[1], v[2]]: dados_vert.extend(vi); dados_vert.extend(normal_vertice(vi))
        for vi in [v[0], v[2], v[3]]: dados_vert.extend(vi); dados_vert.extend(normal_vertice(vi))
    dados_vert = np.array(dados_vert, dtype=np.float32)
    Vao_cubo_vertice = montaVAO(dados_vert)

# -----------------------------
# Pirâmide: normais de face e de vértice
# -----------------------------

def inicializaPiramide():
    """
    Constrói a pirâmide em dois VAOs.

    A pirâmide é um caso interessante: suas faces são completamente planas, então
    a normal de face é matematicamente "correta". A normal de vértice suaviza
    as arestas laterais — especialmente perceptível no topo, onde 4 faces se encontram.
    """
    global Vao_pir_face, Vao_pir_vertice, Tri_piramide

    topo = np.array([ 0.0,  0.8,  0.0], dtype=np.float32)
    ffd  = np.array([-0.5, -0.4,  0.5], dtype=np.float32)
    ffe  = np.array([ 0.5, -0.4,  0.5], dtype=np.float32)
    tfd  = np.array([-0.5, -0.4, -0.5], dtype=np.float32)
    tfe  = np.array([ 0.5, -0.4, -0.5], dtype=np.float32)

    triangulos = [
        (topo, ffd, ffe),
        (topo, ffe, tfe),
        (topo, tfe, tfd),
        (topo, tfd, ffd),
        (ffd,  tfd, tfe),
        (ffd,  tfe, ffe),
    ]

    # --- VAO com normais de FACE ---
    dados_face = []
    for v0, v1, v2 in triangulos:
        n = calculaNormal(v0, v1, v2)
        for vi in [v0, v1, v2]: dados_face.extend(vi); dados_face.extend(n)
    dados_face = np.array(dados_face, dtype=np.float32)
    Tri_piramide = len(dados_face) // 18
    Vao_pir_face = montaVAO(dados_face)

    # --- VAO com normais de VÉRTICE ---
    # Acumula normais de face por vértice único e faz a média.
    normais_por_vertice = {}
    for v0, v1, v2 in triangulos:
        n = calculaNormal(v0, v1, v2)
        for v in [v0, v1, v2]:
            chave = tuple(np.round(v, 5))
            if chave not in normais_por_vertice:
                normais_por_vertice[chave] = []
            normais_por_vertice[chave].append(n)

    def normal_vertice(v):
        chave = tuple(np.round(v, 5))
        ns = normais_por_vertice[chave]
        media = np.mean(ns, axis=0)
        return media / np.linalg.norm(media)

    dados_vert = []
    for v0, v1, v2 in triangulos:
        for vi in [v0, v1, v2]: dados_vert.extend(vi); dados_vert.extend(normal_vertice(vi))
    dados_vert = np.array(dados_vert, dtype=np.float32)
    Vao_pir_vertice = montaVAO(dados_vert)

# -----------------------------
# Esfera: normais de face e de vértice
# -----------------------------

def inicializaEsfera():
    """
    Constrói a esfera em dois VAOs.

    Este é o caso mais dramático: com poucos triângulos e normais de face,
    a natureza poligonal da malha é completamente visível — cada faceta tem
    brilho uniforme e os limites entre triângulos são evidentes.

    Com normais de vértice, a mesma geometria parece uma esfera perfeita.
    Isso demonstra algo fundamental: a normal de vértice é uma ILUSÃO ÓPTICA —
    ela não muda a geometria (os triângulos planos permanecem planos), apenas
    instrui o shader a calcular o brilho como se a superfície fosse curva.

    Normal de vértice da esfera:
      Para uma esfera centrada na origem, a normal em qualquer ponto da superfície
      aponta radialmente para fora — é simplesmente a posição do vértice normalizada.
      Essa é a normal analítica "perfeita" da esfera, usada como normal de vértice.
    """
    global Vao_esf_face, Vao_esf_vertice, Tri_esfera

    rings   = Resolucao_esfera
    sectors = Resolucao_esfera
    raio    = 0.8

    dados_face = []
    dados_vert = []

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

            # Normais de VÉRTICE para a esfera: aponta radialmente para fora
            # (posição na superfície unitária = direção da normal)
            nv00 = v00 / np.linalg.norm(v00) if np.linalg.norm(v00) > 1e-8 else np.array([0,1,0], np.float32)
            nv01 = v01 / np.linalg.norm(v01) if np.linalg.norm(v01) > 1e-8 else np.array([0,1,0], np.float32)
            nv10 = v10 / np.linalg.norm(v10) if np.linalg.norm(v10) > 1e-8 else np.array([0,1,0], np.float32)
            nv11 = v11 / np.linalg.norm(v11) if np.linalg.norm(v11) > 1e-8 else np.array([0,1,0], np.float32)

            # --- Triângulo 1 ---
            nf1 = calculaNormal(v00, v10, v11)  # normal de face

            # Face
            for vi in [v00, v10, v11]: dados_face.extend(vi); dados_face.extend(nf1)
            # Vértice
            for vi, nvi in [(v00, nv00), (v10, nv10), (v11, nv11)]:
                dados_vert.extend(vi); dados_vert.extend(nvi)

            # --- Triângulo 2 ---
            nf2 = calculaNormal(v00, v11, v01)  # normal de face

            # Face
            for vi in [v00, v11, v01]: dados_face.extend(vi); dados_face.extend(nf2)
            # Vértice
            for vi, nvi in [(v00, nv00), (v11, nv11), (v01, nv01)]:
                dados_vert.extend(vi); dados_vert.extend(nvi)

    dados_face = np.array(dados_face, dtype=np.float32)
    dados_vert = np.array(dados_vert, dtype=np.float32)
    Tri_esfera = len(dados_face) // 18
    Vao_esf_face    = montaVAO(dados_face)
    Vao_esf_vertice = montaVAO(dados_vert)

# -----------------------------
# Shaders
# -----------------------------
# Idêntico ao Exemplo 1: recebe normal via atributo 1 e aplica iluminação direcional
# simples com direção fixa hardcoded. A diferença visual entre os modos vem
# inteiramente dos dados de normal no VBO — o shader não sabe qual modo está ativo.

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
            gl_Position  = proj * view * transform * vec4(vertex_posicao, 1.0);
            // Transforma a normal para o espaço do mundo usando apenas a parte
            // rotação/escala da matriz de transformação (ignora translação)
            normal_mundo = mat3(transform) * vertex_normal;
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
            // para tornar a diferença entre os tipos de normal visível.
            vec3  n           = normalize(normal_mundo);
            float difuso      = max(dot(n, luz_dir), 0.0) * 0.8;
            float ambiente    = 0.2;
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
    modo_str = "VÉRTICE (suave)  " if Modo_normal_vertice else "FACE (facetada)  "
    total    = Tri_cubo + Tri_piramide + Tri_esfera
    print(
        f"\r[Normal: {modo_str}]  "
        f"Res. esfera: {Resolucao_esfera:2d}x{Resolucao_esfera:<2d}  |  "
        f"Total tri: {total:5d}  |  "
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

    print("\n--- Exemplo: Normal de Face vs. Normal de Vértice ---")
    print("  N      — alternar modo de normal (FACE facetada / VÉRTICE suave)")
    print("  +/-    — mais/menos triângulos na esfera")
    print("  F      — wireframe on/off")
    print("  W/A/S/D + mouse — câmera FPS")
    print("  ESC    — fechar\n")
    print("  Experimento sugerido:")
    print("    1. Deixe a esfera com poucos triângulos (-) e ative wireframe (F)")
    print("    2. Veja a forma claramente poligonal — faces planas visíveis")
    print("    3. Desative wireframe (F) e alterne a normal (N)")
    print("    4. A MESMA geometria parece uma esfera perfeita — ilusão óptica!\n")
    print("  Nota: a variação de brilho é apenas um recurso visual para tornar")
    print("  as normais perceptíveis. A luz orbita automaticamente a cena.")
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

        # Seleciona os VAOs do modo de normal ativo.
        # A troca é instantânea: apenas muda qual VAO é vinculado — o shader é o mesmo.
        # Isso demonstra que a diferença visual vem APENAS dos dados de normal no VBO.
        vao_cubo = Vao_cubo_vertice  if Modo_normal_vertice else Vao_cubo_face
        vao_pir  = Vao_pir_vertice   if Modo_normal_vertice else Vao_pir_face
        vao_esf  = Vao_esf_vertice   if Modo_normal_vertice else Vao_esf_face

        # --- Cubo (esquerda) — azul ---
        glBindVertexArray(vao_cubo)
        defineCor(0.3, 0.6, 1.0, 1.0)
        transformacaoGenerica(-2.5, 0, 0,  1, 1, 1,  20, 30, 0)
        glDrawArrays(GL_TRIANGLES, 0, Tri_cubo * 3)

        # --- Pirâmide (centro) — laranja ---
        glBindVertexArray(vao_pir)
        defineCor(1.0, 0.6, 0.2, 1.0)
        transformacaoGenerica(0, 0, 0,  1, 1, 1,  0, 20, 0)
        glDrawArrays(GL_TRIANGLES, 0, Tri_piramide * 3)

        # --- Esfera (direita) — verde ---
        glBindVertexArray(vao_esf)
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