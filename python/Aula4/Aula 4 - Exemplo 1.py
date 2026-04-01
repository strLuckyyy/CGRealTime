# Triângulos vs Custo de Renderização - exemplo para a disciplina de Computação Gráfica em Tempo Real
#
# Este exemplo demonstra que o custo de renderização não depende apenas
# do número de triângulos - ele depende também de onde está o gargalo da GPU.
#
# Três configurações de malha (LOD) são comparadas:
#   LOD A -   5.000 triângulos  (50 × 50 subdivisões)
#   LOD B -  49.928 triângulos  (158 × 158 subdivisões)
#   LOD C - 500.000 triângulos  (500 × 500 subdivisões)
#
# Dois shaders de fragmento são disponibilizados:
#   Simples - apenas lê uma cor uniforme e a escreve no fragmento
#   Pesado  - executa 80 iterações de operações trigonométricas por fragmento
#             (simula um shader caro, como o de iluminação complexa ou PBR)
#
# Modos de visualização adicionais:
#   Wireframe        - exibe apenas as arestas dos triângulos, sem preenchimento
#   Overdraw heatmap - acumula fragmentos com blending aditivo para revelar
#                      regiões desenhadas múltiplas vezes (overdraw)
#
# Controles:
#   W/A/S/D   - mover câmera (FPS)
#   Mouse     - girar câmera
#   1         - alternar LOD (A → B → C → A)
#   2         - wireframe on/off
#   4         - shader simples / pesado
#   5         - overdraw heatmap on/off
#   ESC       - fechar
#
# HUD no título da janela (atualizado a cada segundo):
#   LOD atual, triângulos, FPS, estados ativos

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import math

# -----------------------------
# Configuração geral
# -----------------------------

WIDTH  = 800
HEIGHT = 600

Window = None

# Dois programas de shader: simples (cor uniforme) e pesado (cálculo intensivo por fragmento)
Shader_programm_simples = None
Shader_programm_pesado  = None
Shader_programm         = None  # aponta para o programa ativo no momento

# Câmera FPS
Cam_speed = 10.0
Cam_pos   = np.array([0.0, 0.0, 2.0], dtype=np.float32)
Cam_yaw   =   -90.0
Cam_pitch =   0.0

lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

Tempo_entre_frames = 0.0  # variável utilizada para movimentar a câmera

# -----------------------------
# Malhas LOD
# -----------------------------
# Três malhas são geradas com resoluções crescentes.
# Cada uma representa um "nível de detalhe" (LOD) da mesma esfera.
# O usuário alterna entre elas com a tecla 1 para observar o impacto no FPS.

Malha_vaos            = []  # VAO de cada LOD
Malha_vbos            = []  # VBO de cada LOD
Malha_qtd_vertices    = []  # quantidade de vértices para glDrawArrays
Malha_qtd_triangulos  = []  # triângulos = vértices / 3
LOD_index             = 0   # qual malha está ativa (0 = A, 1 = B, 2 = C)

# -----------------------------
# Estados do experimento
# -----------------------------

# Wireframe: exibe apenas as arestas dos triângulos, sem preenchimento
Wireframe_ativo = False

# Shader pesado: substitui o fragment shader por um que faz 80 iterações trigonométricas,
# simulando um shader caro (PBR, iluminação complexa, etc.)
Shader_pesado_ativo = False

# Overdraw heatmap: usa blending aditivo para acumular fragmentos em vez de sobrescrever.
# Regiões desenhadas várias vezes ficam mais claras - revela onde há overdraw.
Overdraw_ativo = False

# -----------------------------
# Detecção de borda de tecla (edge detection)
# -----------------------------
# Dicionário que guarda o estado de cada tecla no frame anterior.
# Usado para detectar o momento exato em que uma tecla é pressionada (edge rising),
# evitando que um único toque dispare a ação múltiplas vezes.
_estado_tecla_anterior = {}

# -----------------------------
# Acumuladores do HUD
# -----------------------------

_hud_acumulado    = 0.0
_hud_qtd_frames   = 0

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
    Cam_yaw   += xoffset * sensibilidade
    Cam_pitch += yoffset * sensibilidade

    Cam_pitch = max(-89.0, min(89.0, Cam_pitch))

# Detecta se uma tecla foi pressionada neste frame (e não estava no anterior).
# Retorna True apenas no primeiro frame em que a tecla está pressionada.
def teclaPressionadaUmaVez(key):
    atual    = glfw.get_key(Window, key) == glfw.PRESS
    anterior = _estado_tecla_anterior.get(key, False)
    _estado_tecla_anterior[key] = atual
    return atual and (not anterior)  # True apenas na transição False → True

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    # Inicializa GLFW
    glfw.init()

    # Criação de uma janela
    Window = glfw.create_window(WIDTH, HEIGHT, 'Triângulos vs Custo - CG em Tempo Real', None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.set_window_size_callback(Window, redimensionaCallback)
    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)

    print("Placa de vídeo: ", glGetString(GL_RENDERER))
    print("Versão do OpenGL: ", glGetString(GL_VERSION))

# -----------------------------
# Geração da esfera UV
# -----------------------------

def geraEsferaTriangulada(raio, stacks, slices):
    """
    Gera uma esfera UV sem índice (vértices duplicados, pronta para glDrawArrays).

    A posição de cada vértice é calculada por:
      x = raio * sin(phi) * cos(theta)
      y = raio * cos(phi)
      z = raio * sin(phi) * sin(theta)

    Cada célula da grade esférica gera dois triângulos.
    Total de triângulos ≈ 2 × stacks × slices.

    Quanto maiores stacks e slices, mais triângulos e mais suave a superfície,
    porém maior o custo de renderização - é exatamente isso que este exemplo mede.
    """
    vertices = []

    for i in range(stacks):
        phi0 = math.pi * (i       / stacks)
        phi1 = math.pi * ((i + 1) / stacks)

        for j in range(slices):
            theta0 = 2.0 * math.pi * (j       / slices)
            theta1 = 2.0 * math.pi * ((j + 1) / slices)

            # Função auxiliar: calcula um ponto na superfície da esfera
            def p(phi, theta):
                return [
                    raio * math.sin(phi) * math.cos(theta),
                    raio * math.cos(phi),
                    raio * math.sin(phi) * math.sin(theta)
                ]

            p00 = p(phi0, theta0)
            p10 = p(phi1, theta0)
            p01 = p(phi0, theta1)
            p11 = p(phi1, theta1)

            # Triângulo 1: p00, p10, p11
            vertices += p00 + p10 + p11

            # Triângulo 2: p00, p11, p01
            vertices += p00 + p11 + p01

    return np.array(vertices, dtype=np.float32)

# -----------------------------
# Inicialização das geometrias
# -----------------------------

def criaMalha(pontos):
    """
    Cria e retorna um VAO a partir de um array numpy de posições (x, y, z).
    Formato esperado: [x, y, z, x, y, z, ...]
    """
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, pontos, GL_STATIC_DRAW)

    # Atributo 0: posição (x, y, z) - 3 floats, stride = 0 (dados contíguos)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

    glBindVertexArray(0)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    qtd_vertices = int(pontos.size // 3)
    return vao, vbo, qtd_vertices


def inicializaMalhasLOD():
    configs = [
        ("LOD A",  50,  50),   #  ~  5.000 triângulos
        ("LOD B", 158, 158),   #  ~ 49.928 triângulos
        ("LOD C", 500, 500),   #  ~500.000 triângulos
    ]

    for nome, stacks, slices in configs:
        pontos = geraEsferaTriangulada(0.75, stacks, slices)
        vao, vbo, qtd_v = criaMalha(pontos)

        Malha_vaos.append(vao)
        Malha_vbos.append(vbo)
        Malha_qtd_vertices.append(qtd_v)
        Malha_qtd_triangulos.append(qtd_v // 3)

        print(f"{nome}: stacks={stacks}, slices={slices}, tris={qtd_v // 3}")

# -----------------------------
# Shaders
# -----------------------------
# O vertex shader é o mesmo para os dois programas: recebe a posição do vértice
# e aplica as matrizes de transformação, câmera e projeção.
#
# O fragment shader simples apenas escreve uma cor uniforme - custo mínimo.
# O fragment shader pesado executa 80 iterações de sin/cos por fragmento,
# simulando o tipo de carga presente em shaders reais de iluminação.
# A diferença de FPS entre os dois revela se o gargalo está no fragmento ou no vértice.

def inicializaShaders():
    global Shader_programm_simples, Shader_programm_pesado, Shader_programm

    # Especificação do Vertex Shader (compartilhado pelos dois programas):
    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        // transform - matriz de modelo recebida do Python
        // view      - matriz da câmera recebida do Python
        // proj      - matriz de projeção recebida do Python
        uniform mat4 transform, view, proj;
        void main() {
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
        }
    """

    # Especificação do Fragment Shader simples:
    # Apenas lê a cor uniforme e a escreve no fragmento - custo praticamente zero.
    fragment_simples = """
        #version 400
        out vec4 frag_colour;
        uniform vec4 corobjeto;
        void main() {
            frag_colour = corobjeto;
        }
    """

    # Especificação do Fragment Shader pesado:
    # Executa 80 iterações de operações trigonométricas por fragmento.
    # Isso simula shaders reais caros (PBR, subsurface scattering, etc.).
    # O objetivo é saturar o estágio de fragmento para revelar esse gargalo.
    fragment_pesado = """
        #version 400
        out vec4 frag_colour;
        uniform vec4 corobjeto;
        void main() {
            vec2  p   = gl_FragCoord.xy * 0.002;
            float acc = 0.0;

            // 80 iterações de sin/cos - carga artificial no fragment shader
            for (int i = 0; i < 80; ++i) {
                p = vec2(
                    sin(p.x * 1.7 + p.y * 1.3 + float(i) * 0.02),
                    cos(p.y * 1.5 - p.x * 1.1 + float(i) * 0.03)
                );
                acc += p.x * p.y;
            }

            // Mistura a cor do objeto com verde conforme a intensidade acumulada
            float m = clamp(abs(acc) * 0.02, 0.0, 1.0);
            frag_colour = mix(corobjeto, vec4(0.2, 0.9, 0.3, 1.0), m);
        }
    """

    # Compilação do vertex shader (reutilizado pelos dois programas)
    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)

    # Especificação dos Shader Programs:
    fs_simples = OpenGL.GL.shaders.compileShader(fragment_simples, GL_FRAGMENT_SHADER)
    Shader_programm_simples = OpenGL.GL.shaders.compileProgram(vs, fs_simples)
    glDeleteShader(fs_simples)

    fs_pesado = OpenGL.GL.shaders.compileShader(fragment_pesado, GL_FRAGMENT_SHADER)
    Shader_programm_pesado = OpenGL.GL.shaders.compileProgram(vs, fs_pesado)
    glDeleteShader(fs_pesado)

    glDeleteShader(vs)

    Shader_programm = Shader_programm_simples  # começa com o shader simples

# -----------------------------
# Transformação de modelo
# -----------------------------

def transformacaoGenerica(Tx, Ty, Tz, Sx, Sy, Sz, Rx, Ry, Rz):
    # Constrói a matriz de transformação: translação × rotação × escala
    translacao = np.array([
        [1, 0, 0, Tx],
        [0, 1, 0, Ty],
        [0, 0, 1, Tz],
        [0, 0, 0,  1]
    ], dtype=np.float32)

    rx, ry, rz = np.radians([Rx, Ry, Rz])

    # matriz de rotação em torno do eixo X
    rotacaoX = np.array([
        [1,           0,            0, 0],
        [0, np.cos(rx), -np.sin(rx), 0],
        [0, np.sin(rx),  np.cos(rx), 0],
        [0,           0,            0, 1]
    ], dtype=np.float32)

    # matriz de rotação em torno do eixo Y
    rotacaoY = np.array([
        [ np.cos(ry), 0, np.sin(ry), 0],
        [           0, 1,           0, 0],
        [-np.sin(ry), 0, np.cos(ry), 0],
        [           0, 0,           0, 1]
    ], dtype=np.float32)

    # matriz de rotação em torno do eixo Z
    rotacaoZ = np.array([
        [np.cos(rz), -np.sin(rz), 0, 0],
        [np.sin(rz),  np.cos(rz), 0, 0],
        [          0,           0, 1, 0],
        [          0,           0, 0, 1]
    ], dtype=np.float32)

    # matriz de escala
    escala = np.array([
        [Sx,  0,  0, 0],
        [ 0, Sy,  0, 0],
        [ 0,  0, Sz, 0],
        [ 0,  0,  0, 1]
    ], dtype=np.float32)

    transformacaoFinal = translacao @ rotacaoZ @ rotacaoY @ rotacaoX @ escala

    # E passamos a matriz para o Vertex Shader
    loc = glGetUniformLocation(Shader_programm, "transform")
    glUniformMatrix4fv(loc, 1, GL_TRUE, transformacaoFinal)

# -----------------------------
# Câmera (matriz de visualização)
# -----------------------------

def especificaMatrizVisualizacao():
    """
    Implementa um sistema de câmera no estilo FPS usando uma matriz lookAt manual.

    A ideia geral é simular uma câmera no espaço 3D: um ponto (posição) e uma
    direção (para onde ela está olhando). Em vez de mover a câmera, aplicamos
    a transformação inversa no mundo - deslocamos e rotacionamos tudo o que é
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

    cima   = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    s = np.cross(frente, cima); s /= np.linalg.norm(s)
    u = np.cross(s, frente)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] =  s
    view[1, :3] =  u
    view[2, :3] = -frente
    view[0,  3] = -np.dot(s,      Cam_pos)
    view[1,  3] = -np.dot(u,      Cam_pos)
    view[2,  3] =  np.dot(frente, Cam_pos)

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
# Estados de renderização
# -----------------------------

def aplicaEstadosDeRender():
    # Wireframe - exibe apenas as arestas dos triângulos
    if Wireframe_ativo:
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    else:
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    # Overdraw heatmap - acumula fragmentos com blending aditivo.
    # Regiões com muitos fragmentos sobrepostos ficam progressivamente mais claras,
    # revelando visualmente onde a GPU está desperdiçando trabalho com overdraw.
    if Overdraw_ativo:
        glEnable(GL_BLEND)
        glBlendFunc(GL_ONE, GL_ONE)  # blending aditivo: dst = src + dst
        glDepthMask(GL_FALSE)        # desativa escrita no depth buffer durante o heatmap
    else:
        glDisable(GL_BLEND)
        glDepthMask(GL_TRUE)

# -----------------------------
# HUD no título da janela
# -----------------------------

def atualizaHUD(dt):
    global _hud_acumulado, _hud_qtd_frames

    # Acumula frames e tempo para calcular o FPS médio a cada segundo
    _hud_acumulado  += dt
    _hud_qtd_frames += 1

    if _hud_acumulado >= 1.0:
        fps             = _hud_qtd_frames / _hud_acumulado
        _hud_acumulado  = 0.0
        _hud_qtd_frames = 0

        tris  = Malha_qtd_triangulos[LOD_index]
        sh    = "PESADO"  if Shader_pesado_ativo else "SIMPLES"
        wf    = "ON"      if Wireframe_ativo      else "OFF"
        od    = "ON"      if Overdraw_ativo        else "OFF"

        titulo = f"Triângulos vs Custo | LOD={LOD_index} tris={tris} | FPS={fps:.1f} | WF={wf} SH={sh} OD={od}"
        glfw.set_window_title(Window, titulo)

# -----------------------------
# Entrada de teclado
# -----------------------------

def trataTeclado():
    """
    Movimenta a câmera no espaço 3D conforme as teclas WASD,
    e gerencia os toggles do experimento com detecção de borda de tecla.
    """
    global Cam_pos, LOD_index
    global Wireframe_ativo, Shader_pesado_ativo, Overdraw_ativo
    global Shader_programm

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

    # 1 - alterna entre os três LODs (edge detection: dispara uma vez por pressionamento)
    if teclaPressionadaUmaVez(glfw.KEY_1):
        LOD_index = (LOD_index + 1) % 3

    # 2 - wireframe on/off
    if teclaPressionadaUmaVez(glfw.KEY_2):
        Wireframe_ativo = not Wireframe_ativo

    # 4 - alterna entre shader simples e pesado
    if teclaPressionadaUmaVez(glfw.KEY_4):
        Shader_pesado_ativo = not Shader_pesado_ativo
        Shader_programm     = Shader_programm_pesado if Shader_pesado_ativo else Shader_programm_simples

    # 5 - overdraw heatmap on/off
    if teclaPressionadaUmaVez(glfw.KEY_5):
        Overdraw_ativo = not Overdraw_ativo

# -----------------------------
# Loop de renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames

    tempo_anterior = glfw.get_time()

    # Ativa o teste de profundidade para que faces mais próximas sobreponham as mais distantes
    glEnable(GL_DEPTH_TEST)

    print("\n--- Exemplo: Triângulos vs Custo de Renderização ---")
    print("  1         - alternar LOD (A → B → C → A)")
    print("  2         - wireframe on/off")
    print("  4         - shader simples / pesado")
    print("  5         - overdraw heatmap on/off")
    print("  W/A/S/D + mouse - câmera FPS")
    print("  ESC       - fechar\n")
    print("  Observe o FPS no título da janela ao alternar LOD e shader.")
    print("  Com o shader simples, a diferença entre LODs é pequena.")
    print("  Com o shader pesado, o gargalo muda para o estágio de fragmento.\n")

    while not glfw.window_should_close(Window):
        # Calcula quantos segundos se passaram entre um frame e outro
        tempo_atual        = glfw.get_time()
        Tempo_entre_frames = tempo_atual - tempo_anterior
        tempo_anterior     = tempo_atual

        glViewport(0, 0, WIDTH, HEIGHT)
        glClearColor(0.2, 0.3, 0.3, 1.0)  # define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # limpa os buffers de cor e profundidade

        aplicaEstadosDeRender()

        glUseProgram(Shader_programm)
        inicializaCamera()

        # Seleciona o VAO da malha ativa (LOD A, B ou C)
        glBindVertexArray(Malha_vaos[LOD_index])

        # No modo overdraw, usa uma cor escura para que o acúmulo aditivo
        # revele gradualmente as regiões de sobreposição
        if Overdraw_ativo:
            defineCor(0.03, 0.03, 0.06, 1.0)
            # Desenha a mesma esfera N vezes com offsets que se sobrepõem na projeção
            '''for i in range(8):
                offset = i * 0.05
                transformacaoGenerica(offset, 0, 0,  1, 1, 1,  0, 0, 0)
                glDrawArrays(GL_TRIANGLES, 0, Malha_qtd_vertices[LOD_index])'''
        else:
            transformacaoGenerica(0, 0, 0,  1, 1, 1,  0, 0, 0)

        transformacaoGenerica(0, 0, 0,  1, 1, 1,  0, 0, 0)
        glDrawArrays(GL_TRIANGLES, 0, Malha_qtd_vertices[LOD_index])

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()
        atualizaHUD(Tempo_entre_frames)

    glfw.terminate()

# Função principal
def main():
    inicializaOpenGL()
    inicializaMalhasLOD()
    inicializaShaders()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()