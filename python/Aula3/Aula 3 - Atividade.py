# -----------------------------
#
# Exercício: Construir um Anel 3D (Toroide)
#
# Controles:
#   W/A/S/D                 — mover câmera (FPS)
#   Mouse                   — girar câmera
#   ESC                     — fechar
# 
#  Teclado numérico + / -   — aumentar/diminuir resolução do toroide
#   1                       — alternar exibição de pontos
#   2                       — alternar exibição de wireframe
#   P                       — aumentar tamanho dos pontos
#   O                       — diminuir tamanho dos pontos
#
#   by: Abrahão Francis Gonçalves
#
# -----------------------------

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import math
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

last_tempo_frame = 0.0  # para controle de cooldown de teclas

# VAO Toroide
Vao_Teroide = None
resolucao = 35

# Exibição
tam_pontos = 5
exibir_pontos = False
exibir_wireframe = False #troca entre os triangulos preenchidos e a malha de linhas

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
    Window = glfw.create_window(WIDTH, HEIGHT, 'Teroide — CG em Tempo Real', None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)

    print("Placa de vídeo: ", glGetString(GL_RENDERER))
    print("Versão do OpenGL: ", glGetString(GL_VERSION))

# -----------------------------
# Geometria do Toroide
# -----------------------------

def gerarGeometria(resolucao) -> np.ndarray:
    vbo = []
    R: float = 3
    r: float = .5

    for i in range(resolucao):
        phi = i * (2 * math.pi / resolucao)
        for j in range(resolucao):
            theta = j * (2 * math.pi / resolucao)  

            # Posição de cada vértice
            x = (R + r * math.cos(theta)) * math.cos(phi)
            y = r * math.sin(theta)
            z = (R + r * math.cos(theta)) * math.sin(phi)

            # Cálculo da normal
            c = (R * math.cos(phi), 0, R * math.sin(phi))
            n = np.array([x, y, z]) - np.array(c)
            n /= np.linalg.norm(n)
            
            vbo.extend([x, y, z, n[0], n[1], n[2]])

    return np.array(vbo, np.float32)

def gerarMalha(resolucao):
    ebo = []
    
    for i in range(resolucao):
        for j in range(resolucao):
            # Índices dos 4 cantos de um "quadrado" na malha
            # Usamos o % (módulo) para que o último ponto se conecte ao primeiro (fechar o anel)
            
            p1 = i * resolucao + j
            p2 = ((i + 1) % resolucao) * resolucao + j
            p3 = i * resolucao + ((j + 1) % resolucao)
            p4 = ((i + 1) % resolucao) * resolucao + ((j + 1) % resolucao)

            # Cada quadrado da malha é formado por dois triângulos:
            # Triângulo 1 (p1, p2, p3)
            ebo.extend([p1, p2, p3])
            # Triângulo 2 (p2, p4, p3)
            ebo.extend([p2, p4, p3])
    
    return np.array(ebo, dtype=np.uint32)

# -----------------------------
# Inicialização das geometrias
# -----------------------------

def inicializaGeometria():
    global Vao_Teroide, resolucao

    stride = 6 * 4
    
    # Teroide
    vbo_teroide = gerarGeometria(resolucao)
    vbo_malha   = gerarMalha(resolucao)

    Vao_Teroide = glGenVertexArrays(1)
    glBindVertexArray(Vao_Teroide)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vbo_teroide.nbytes, vbo_teroide, GL_STATIC_DRAW)

    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, vbo_malha.nbytes, vbo_malha, GL_STATIC_DRAW)

    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))

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
        [0.0, 0.0, -1.0, 0.0]
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
    global Cam_pos, resolucao, tam_pontos, exibir_pontos, exibir_wireframe, last_tempo_frame

    velocidade = Cam_speed * Tempo_entre_frames
    tempo_atual = glfw.get_time()
    cd_tecla_LOD = 0.2  # segundos entre mudanças de LOD
    cd_tecla_pontos = .5  # segundos entre mudanças de tamanho de pontos
    cd_tecla_wire = 0.5  # segundos entre mudanças de exibição de wireframe

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

    if tempo_atual - last_tempo_frame > cd_tecla_LOD:    
        # LOD manual
        if glfw.get_key(Window, glfw.KEY_KP_ADD) == glfw.PRESS:
            resolucao += 1
            inicializaGeometria()
            last_tempo_frame = tempo_atual

        if glfw.get_key(Window, glfw.KEY_KP_SUBTRACT) == glfw.PRESS and resolucao > 3:
            resolucao -= 1
            inicializaGeometria()
            last_tempo_frame = tempo_atual

    if tempo_atual - last_tempo_frame > cd_tecla_pontos:
        # Mudar tipo de exibição do modelo
        if glfw.get_key(Window, glfw.KEY_1) == glfw.PRESS:
            exibir_pontos = not exibir_pontos
            last_tempo_frame = tempo_atual
    
    if tempo_atual - last_tempo_frame > cd_tecla_wire:
        if glfw.get_key(Window, glfw.KEY_2) == glfw.PRESS:
            exibir_wireframe = not exibir_wireframe
            last_tempo_frame = tempo_atual
    
    if tempo_atual - last_tempo_frame > cd_tecla_pontos:
        if glfw.get_key(Window, glfw.KEY_P) == glfw.PRESS:
            tam_pontos += 1
            if tam_pontos > 10:
                tam_pontos = 1
            last_tempo_frame = tempo_atual

    if tempo_atual - last_tempo_frame < cd_tecla_pontos:
        if glfw.get_key(Window, glfw.KEY_O) == glfw.PRESS:
            tam_pontos -= 1
            if tam_pontos < 1:
                tam_pontos = 10
            last_tempo_frame = tempo_atual

# -----------------------------
# Loop de renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames, Vao_Teroide, resolucao, tam_pontos, exibir_pontos, exibir_wireframe

    tempo_anterior = glfw.get_time()

    # Ativa o teste de profundidade para que faces mais próximas sobreponham as mais distantes
    glEnable(GL_DEPTH_TEST)

    print("\n\n  W/A/S/D + mouse — câmera FPS")
    print("  ESC             — fechar\n")
    print("  Teclado numérico + / - — aumentar/diminuir resolução do toroide")
    print("  1               — alternar exibição de pontos")
    print("  2               — alternar exibição de wireframe")
    print("  P               — aumentar tamanho dos pontos")
    print("  O               — diminuir tamanho dos pontos")

    while not glfw.window_should_close(Window):
        # Calcula quantos segundos se passaram entre um frame e outro
        tempo_frame_atual  = glfw.get_time()
        Tempo_entre_frames = tempo_frame_atual - tempo_anterior
        tempo_anterior     = tempo_frame_atual

        glClearColor(0.2, 0.3, 0.4, 1.0)  # define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # limpa os buffers de cor e profundidade

        glUseProgram(Shader_programm)
        inicializaCamera()

        # Iluminação
        angulo_luz = tempo_frame_atual * 0.8  # 0.8 rad/s — rotação suave
        luz_x = np.cos(angulo_luz)
        luz_z = np.sin(angulo_luz)
        luz_dir = np.array([luz_x, 0.6, luz_z], dtype=np.float32)
        luz_dir /= np.linalg.norm(luz_dir)
        luzLoc = glGetUniformLocation(Shader_programm, "luz_dir")
        glUniform3fv(luzLoc, 1, luz_dir)

        # Draw Objects # 
        transformLoc = glGetUniformLocation(Shader_programm, "transform")
        glUniformMatrix4fv(transformLoc, 1, GL_TRUE, translacao(0, 0, 0))
        glBindVertexArray(Vao_Teroide)
        
        # Desenha os pontos do toroide
        if exibir_pontos:
            glPointSize(tam_pontos)
            defineCor(0, 0, 1, 1.0)
            glDrawArrays(GL_POINTS, 0, resolucao * resolucao)

        # Desenha a malha do toroide
        if exibir_wireframe:
            defineCor(1, 1, 1, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            defineCor(1, .5, 0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        
        glDrawElements(GL_TRIANGLES, resolucao * resolucao * 6, GL_UNSIGNED_INT, None)

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