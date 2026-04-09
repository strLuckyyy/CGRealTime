# Backface Culling - exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra o conceito de Backface Culling:
# o descarte automático das faces traseiras de objetos opacos antes da rasterização.
#
# Conceitos demonstrados:
# - Winding Order (CCW): a ordem anti-horária dos vértices define a "frente" do polígono
# - Backface Culling: faces cujo winding aparece horário na tela são descartadas pela GPU
# - Ganho de ~50%: em qualquer objeto fechado e opaco, metade das faces está sempre de costas
# - Frontface Culling: curiosidade didática - descarta a frente e exibe o interior do objeto
#
# Controles:
#   W/A/S/D     - mover câmera (FPS)
#   Mouse       - girar câmera
#   C           - alternar modo de culling (SEM / BACKFACE / FRONTFACE)
#   W (tecla)   - wireframe on/off (tecla F)
#   ESC         - fechar
#
# HUD no terminal (a cada ~1 segundo):
#   Modo de culling ativo, faces descartadas (estimativa), FPS médio

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np

Window        = None
Shader_programm = None
Vao_esfera    = None   # usamos uma esfera de alta resolução para o efeito ser visível
WIDTH  = 800
HEIGHT = 600

Tempo_entre_frames = 0  # variavel utilizada para movimentar a camera

# Variáveis referentes a câmera virtual e sua projeção

Cam_speed = 10.0  # velocidade da camera, 10 unidades por segundo
Cam_pos   = np.array([0.0, 0.0, 3.0])  # posicao inicial da câmera
Cam_yaw   = 180.0  # olhando para a origem
Cam_pitch = 0.0    # controle vertical
lastX, lastY  = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# -----------------------------
# Estado da demonstração
# -----------------------------

# Modos de culling:
#   0 -> SEM culling    (GL_FRONT_AND_BACK desativado - todas as faces renderizadas)
#   1 -> BACKFACE       (GL_BACK  - faces traseiras descartadas, ganho de ~50%)
#   2 -> FRONTFACE      (GL_FRONT - apenas interior visível, curiosidade didática)
Modo_culling = 0

# Wireframe
Wireframe = False

# Número de triângulos gerados na esfera (preenchido em inicializaEsfera)
Num_triangulos = 0

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
    global Modo_culling, Wireframe

    if action != glfw.PRESS:
        return

    # C - cicla entre os três modos de culling
    if key == glfw.KEY_C:
        Modo_culling = (Modo_culling + 1) % 3
        nomes = ["SEM culling (todas as faces)", "BACKFACE culling (~50% descartado)", "FRONTFACE culling (interior visível)"]
        print(f"\n[CULLING] {nomes[Modo_culling]}")

    # F - alterna wireframe
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
    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo Backface Culling - CG em Tempo Real", None, None)
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
# Inicialização da geometria: esfera UV
# -----------------------------
# Usamos uma esfera de alta resolução (muitos triângulos) para que o impacto
# do culling seja visível tanto em wireframe quanto no FPS.
#
# A esfera é definida por uma grade UV de anéis (rings) e setores (sectors).
# Cada célula da grade gera 2 triângulos.
#
# IMPORTANTE sobre o Winding Order (CCW):
#   Os vértices de cada triângulo são listados em ordem ANTI-HORÁRIA quando vistos
#   de fora da esfera. Isso define a "frente" de cada face - o lado voltado para fora.
#   Quando a câmera vê uma face de trás, a projeção 2D inverte a ordem para HORÁRIA
#   (área negativa), e a GPU a descarta automaticamente com o culling ativado.

def inicializaEsfera(rings=48, sectors=64, raio=1.0):
    global Vao_esfera, Num_triangulos

    pontos = []

    for r in range(rings):
        for s in range(sectors):
            # Ângulos dos quatro cantos da célula (r, s)
            theta0 = np.pi * r       / rings
            theta1 = np.pi * (r + 1) / rings
            phi0   = 2 * np.pi * s       / sectors
            phi1   = 2 * np.pi * (s + 1) / sectors

            # Quatro vértices da célula esférica
            v00 = np.array([np.sin(theta0)*np.cos(phi0), np.cos(theta0), np.sin(theta0)*np.sin(phi0)]) * raio
            v01 = np.array([np.sin(theta0)*np.cos(phi1), np.cos(theta0), np.sin(theta0)*np.sin(phi1)]) * raio
            v10 = np.array([np.sin(theta1)*np.cos(phi0), np.cos(theta1), np.sin(theta1)*np.sin(phi0)]) * raio
            v11 = np.array([np.sin(theta1)*np.cos(phi1), np.cos(theta1), np.sin(theta1)*np.sin(phi1)]) * raio

            # Triângulo 1 - ordem CCW vista de fora da esfera
            pontos.extend(v00); pontos.extend(v10); pontos.extend(v11)
            # Triângulo 2 - ordem CCW vista de fora da esfera
            pontos.extend(v00); pontos.extend(v11); pontos.extend(v01)

    pontos = np.array(pontos, dtype=np.float32)
    Num_triangulos = len(pontos) // 9  # 3 vértices * 3 coords = 9 floats por triângulo

    Vao_esfera = glGenVertexArrays(1)
    glBindVertexArray(Vao_esfera)

    pvbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, pvbo)
    glBufferData(GL_ARRAY_BUFFER, pontos, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

    print(f"[ESFERA] {Num_triangulos} triângulos gerados ({rings} rings x {sectors} sectors)")

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
    znear  = 0.1    # recorte z-near
    zfar   = 100.0  # recorte z-far
    fov    = np.radians(67.0)  # campo de visão
    aspecto = WIDTH / HEIGHT   # aspecto

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
# Aplicação do modo de culling
# -----------------------------
# Ativa ou desativa o GL_CULL_FACE conforme o modo atual.
# O OpenGL descarta faces com winding horário (área 2D negativa) na tela.
#
# Modo 0 - SEM culling:
#   glDisable(GL_CULL_FACE) → todas as faces chegam ao rasterizador.
#
# Modo 1 - BACKFACE culling:
#   glEnable(GL_CULL_FACE) + glCullFace(GL_BACK) → faces traseiras descartadas.
#   Como ~50% da esfera está sempre de costas, metade dos triângulos é eliminada
#   antes mesmo de chegar ao Fragment Shader - ganho imediato de desempenho.
#
# Modo 2 - FRONTFACE culling:
#   glEnable(GL_CULL_FACE) + glCullFace(GL_FRONT) → faces frontais descartadas.
#   O interior da esfera fica visível. Útil para debugar winding order,
#   ou para renderizar o interior de ambientes fechados.

def aplicaMododeCulling():
    if Modo_culling == 0:
        # Sem culling - renderiza frente e verso de cada face
        glDisable(GL_CULL_FACE)
    elif Modo_culling == 1:
        # Backface culling - descarta faces traseiras (winding horário na tela)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        # glFrontFace(GL_CCW) é o padrão do OpenGL - não precisa ser chamado explicitamente,
        # mas vale mencionar: CCW (Counter-Clockwise) = frente do polígono.
    elif Modo_culling == 2:
        # Frontface culling - descarta faces frontais (curiosidade pedagógica)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_FRONT)

# -----------------------------
# HUD no terminal
# -----------------------------

def atualizaHUD(fps):
    nomes  = ["SEM culling       ", "BACKFACE culling  ", "FRONTFACE culling "]
    # Estimativa de faces descartadas:
    #   Modo 0: nenhuma descartada
    #   Modo 1: ~50% descartadas (metade traseira do objeto fechado)
    #   Modo 2: ~50% descartadas (metade frontal)
    descartadas = ["~0%  ", "~50% ", "~50% "]

    print(
        f"\r[{nomes[Modo_culling]}]  "
        f"Triângulos totais: {Num_triangulos:5d}  |  "
        f"Faces descartadas: {descartadas[Modo_culling]}  |  "
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

    print("\n--- Exemplo: Backface Culling ---")
    print("  C      - alternar modo de culling (SEM / BACKFACE / FRONTFACE)")
    print("  F      - wireframe on/off  (ative para ver os triângulos!)")
    print("  W/A/S/D + mouse - câmera FPS")
    print("  ESC    - fechar\n")
    print("  Dica: ative o wireframe (F) para ver os triângulos sumindo com o culling!")

    while not glfw.window_should_close(Window):
        # calcula quantos segundos se passaram entre um frame e outro
        tempo_frame_atual  = glfw.get_time()
        Tempo_entre_frames = tempo_frame_atual - tempo_anterior
        tempo_anterior     = tempo_frame_atual

        glClearColor(0.15, 0.15, 0.2, 1.0)  # define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # limpa o buffer de cores e de profundidade
        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)

        # Aplica o modo de culling escolhido pelo aluno antes de desenhar
        aplicaMododeCulling()

        inicializaCamera()

        glBindVertexArray(Vao_esfera)

        # Cor varia conforme o modo para facilitar a identificação visual:
        #   azul  → sem culling (tudo visível) → todos os triângulos chegam ao rasterizador, frente e verso de cada face. Em wireframe, a esfera parece uma bola sólida de arame.
        #   verde → backface (modo normal, ganho de desempenho) → faces com winding horário na tela são descartadas. Em wireframe, a metade traseira da esfera some instantaneamente - o aluno vê exatamente o "ganho de 50%" citado nos slides.
        #   laranja → frontface (interior visível) → descarta a frente, exibe o interior. Conecta com o slide do Winding Order - o aluno entende que a "frente" é uma convenção matemática, não uma propriedade física.
        if Modo_culling == 0:
            defineCor(0.3, 0.6, 1.0, 1.0)   # azul
        elif Modo_culling == 1:
            defineCor(0.3, 0.9, 0.4, 1.0)   # verde
        else:
            defineCor(1.0, 0.6, 0.2, 1.0)   # laranja

        transformacaoGenerica(0, 0, 0, 1, 1, 1, 0, 0, 0)
        glDrawArrays(GL_TRIANGLES, 0, Num_triangulos * 3)

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
    inicializaEsfera(rings=48, sectors=64)  # esfera de alta resolução: ~6144 triângulos
    inicializaRenderizacao()

if __name__ == "__main__":
    main()