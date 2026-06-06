# Câmera e exemplo base para a disciplina de Computação Gráfica em Tempo Real e Computação Gráfica Avançada
#
# Este código serve como base para toda a disciplina.
# Ele implementa:
# - OpenGL moderno (pipeline programável)
# - Um modelo geométrico simples (cubo)
# - Transformações de modelo, visualização (câmera) e projeção
# - Uma câmera no estilo FPS (yaw + pitch)
#
# ADIÇÃO:
# - Animação Procedural utilizando Curvas de Bézier Cúbicas.
# - O parâmetro 't' é vinculado ao tempo real da aplicação para guiar o objeto espacialmente.

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np

Window = None
Shader_programm = None
Vao_cubo = None

WIDTH = 800
HEIGHT = 600

Tempo_entre_frames = 0.0

# -----------------------------
# Parâmetros da câmera virtual
# -----------------------------

Cam_speed = 10.0          # velocidade de deslocamento da câmera
Cam_yaw_speed = 30.0      # velocidade de rotação horizontal
# Posição ajustada para visualizar a trajetória de cima
Cam_pos = np.array([0.0, 15.0, -15.0])  
Cam_yaw = 0.0             
Cam_pitch = -35.0         # Rotação vertical para olhar para baixo

lastX, lastY = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# -----------------------------
# Variáveis da Animação (Bézier)
# -----------------------------

# Pontos de controle da curva cúbica definindo a trajetória espacial.
Ponto_Controle_0 = np.array([-10.0,  0.0,  0.0])
Ponto_Controle_1 = np.array([ -5.0,  0.0, 15.0])
Ponto_Controle_2 = np.array([  5.0,  0.0, 15.0])
Ponto_Controle_3 = np.array([ 10.0,  0.0,  0.0])

# -----------------------------
# Callbacks de janela e entrada
# -----------------------------

def redimensionaCallback(window, w, h):
    global WIDTH, HEIGHT
    WIDTH = w
    HEIGHT = h

def mouse_callback(window, xpos, ypos):
    global lastX, lastY, primeiro_mouse, Cam_yaw, Cam_pitch

    if primeiro_mouse:
        lastX, lastY = xpos, ypos
        primeiro_mouse = False

    xoffset = xpos - lastX
    yoffset = lastY - ypos
    lastX, lastY = xpos, ypos

    sensibilidade = 0.1
    xoffset *= sensibilidade
    yoffset *= sensibilidade

    Cam_yaw += xoffset
    Cam_pitch += yoffset

    Cam_pitch = max(-89.0, min(89.0, Cam_pitch))

def key_callback(window, key, scancode, action, mode):
    return

# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    glfw.init()

    Window = glfw.create_window(WIDTH, HEIGHT, "Animação Procedural com Bézier", None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.set_window_size_callback(Window, redimensionaCallback)
    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)
    glfw.set_key_callback(Window, key_callback)

    print("Placa de vídeo:", glGetString(GL_RENDERER))
    print("Versão do OpenGL:", glGetString(GL_VERSION))

# -----------------------------
# Matemática das Curvas de Bézier
# -----------------------------

def calculaPosicaoBezierCubica(p0, p1, p2, p3, t):
    """
    Equação polinomial paramétrica da curva cúbica de Bézier.
    P(t) = (1-t)³*P0 + 3*(1-t)²*t*P1 + 3*(1-t)*t²*P2 + t³*P3
    
    Retorna a coordenada (X, Y, Z) exata onde o objeto deve estar no instante 't'.
    """
    u = 1.0 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t

    ponto = (uuu * p0) + (3 * uu * t * p1) + (3 * u * tt * p2) + (ttt * p3)
    return ponto

def calculaTangenteBezierCubica(p0, p1, p2, p3, t):
    """
    Calcula a derivada da curva de Bézier no instante 't' para obter o vetor tangente.
    """
    u = 1.0 - t
    uu = u * u
    tt = t * t

    tangente = 3 * uu * (p1 - p0)           
    tangente += 6 * u * t * (p2 - p1)       
    tangente += 3 * tt * (p3 - p2)          
    
    norma = np.linalg.norm(tangente)
    if norma > 0:
        tangente = tangente / norma
        
    return tangente

# -----------------------------
# Inicialização da geometria
# -----------------------------

def inicializaCubo():
    global Vao_cubo

    Vao_cubo = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo)

    points = [
        # face frontal
        0.5,  0.5,  0.5,   0.5, -0.5,  0.5,  -0.5, -0.5,  0.5,
        0.5,  0.5,  0.5,  -0.5, -0.5,  0.5,  -0.5,  0.5,  0.5,
        # face traseira
        0.5,  0.5, -0.5,   0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,
        0.5,  0.5, -0.5,  -0.5, -0.5, -0.5,  -0.5,  0.5, -0.5,
        # face esquerda
       -0.5, -0.5,  0.5,  -0.5,  0.5,  0.5,  -0.5, -0.5, -0.5,
       -0.5, -0.5, -0.5,  -0.5,  0.5, -0.5,  -0.5,  0.5,  0.5,
        # face direita
        0.5, -0.5,  0.5,   0.5,  0.5,  0.5,   0.5, -0.5, -0.5,
        0.5, -0.5, -0.5,   0.5,  0.5, -0.5,   0.5,  0.5,  0.5,
        # face inferior
       -0.5, -0.5,  0.5,   0.5, -0.5,  0.5,   0.5, -0.5, -0.5,
        0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,  -0.5, -0.5,  0.5,
        # face superior
       -0.5,  0.5,  0.5,   0.5,  0.5,  0.5,   0.5,  0.5, -0.5,
        0.5,  0.5, -0.5,  -0.5,  0.5, -0.5,  -0.5,  0.5,  0.5,
    ]

    points = np.array(points, dtype=np.float32)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, points, GL_STATIC_DRAW)

    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

# -----------------------------
# Shaders
# -----------------------------

def inicializaShaders():
    global Shader_programm

    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;

        uniform mat4 transform;
        uniform mat4 view;
        uniform mat4 proj;

        void main() {
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
        }
    """

    fragment_shader = """
        #version 400
        out vec4 frag_colour;
        uniform vec4 corobjeto;

        void main() {
            frag_colour = corobjeto;
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    fs = OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    Shader_programm = OpenGL.GL.shaders.compileProgram(vs, fs)

    glDeleteShader(vs)
    glDeleteShader(fs)

# -----------------------------
# Transformação de modelo
# -----------------------------

def transformacaoGenerica(Tx, Ty, Tz, Sx, Sy, Sz, Rx, Ry, Rz):
    translacao = np.array([
        [1, 0, 0, Tx],
        [0, 1, 0, Ty],
        [0, 0, 1, Tz],
        [0, 0, 0, 1]
    ], dtype=np.float32)

    rx, ry, rz = np.radians([Rx, Ry, Rz])

    rotX = np.array([
        [1, 0, 0, 0],
        [0, np.cos(rx), -np.sin(rx), 0],
        [0, np.sin(rx),  np.cos(rx), 0],
        [0, 0, 0, 1]
    ], dtype=np.float32)

    rotY = np.array([
        [ np.cos(ry), 0, np.sin(ry), 0],
        [0, 1, 0, 0],
        [-np.sin(ry), 0, np.cos(ry), 0],
        [0, 0, 0, 1]
    ], dtype=np.float32)

    rotZ = np.array([
        [np.cos(rz), -np.sin(rz), 0, 0],
        [np.sin(rz),  np.cos(rz), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ], dtype=np.float32)

    escala = np.array([
        [Sx, 0, 0, 0],
        [0, Sy, 0, 0],
        [0, 0, Sz, 0],
        [0, 0, 0, 1]
    ], dtype=np.float32)

    transform = translacao @ rotZ @ rotY @ rotX @ escala

    loc = glGetUniformLocation(Shader_programm, "transform")
    glUniformMatrix4fv(loc, 1, GL_TRUE, transform)

# -----------------------------
# Câmera (matriz de visualização)
# -----------------------------

def especificaMatrizVisualizacao():
    global Cam_pos, Cam_yaw, Cam_pitch

    front = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    front /= np.linalg.norm(front)

    up = np.array([0.0, 1.0, 0.0])
    s = np.cross(front, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, front)

    view = np.identity(4, dtype=np.float32)
    view[0, :3] = s
    view[1, :3] = u
    view[2, :3] = -front
    view[0, 3] = -np.dot(s, Cam_pos)
    view[1, 3] = -np.dot(u, Cam_pos)
    view[2, 3] =  np.dot(front, Cam_pos)

    loc = glGetUniformLocation(Shader_programm, "view")
    glUniformMatrix4fv(loc, 1, GL_TRUE, view)

# -----------------------------
# Projeção
# -----------------------------

def especificaMatrizProjecao():
    znear, zfar = 0.1, 100.0
    fov = np.radians(67.0)
    aspecto = WIDTH / HEIGHT

    a = 1 / (np.tan(fov / 2) * aspecto)
    b = 1 / np.tan(fov / 2)
    c = (zfar + znear) / (znear - zfar)
    d = (2 * znear * zfar) / (znear - zfar)

    proj = np.array([
        [a, 0, 0, 0],
        [0, b, 0, 0],
        [0, 0, c, d],
        [0, 0, -1, 1]
    ], dtype=np.float32)

    loc = glGetUniformLocation(Shader_programm, "proj")
    glUniformMatrix4fv(loc, 1, GL_TRUE, proj)

def inicializaCamera():
    especificaMatrizVisualizacao()
    especificaMatrizProjecao()

# -----------------------------
# Entrada de teclado
# -----------------------------

def trataTeclado():
    global Cam_pos, Tempo_entre_frames

    velocidade = Cam_speed * Tempo_entre_frames

    frente = np.array([
        np.cos(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_pitch)),
        np.sin(np.radians(Cam_yaw)) * np.cos(np.radians(Cam_pitch))
    ])
    frente /= np.linalg.norm(frente)

    direita = np.cross(frente, np.array([0.0, 1.0, 0.0]))
    direita /= np.linalg.norm(direita)

    if glfw.get_key(Window, glfw.KEY_W) == glfw.PRESS:
        Cam_pos += frente * velocidade
    if glfw.get_key(Window, glfw.KEY_S) == glfw.PRESS:
        Cam_pos -= frente * velocidade
    if glfw.get_key(Window, glfw.KEY_A) == glfw.PRESS:
        Cam_pos -= direita * velocidade
    if glfw.get_key(Window, glfw.KEY_D) == glfw.PRESS:
        Cam_pos += direita * velocidade
    if glfw.get_key(Window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(Window, True)

# -----------------------------
# Renderização e Animação
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames

    tempo_anterior = glfw.get_time()
    
    # Define quanto tempo (em segundos) o objeto leva para ir de t=0 até t=1
    duracao_ciclo = 4.0 

    glEnable(GL_DEPTH_TEST)

    while not glfw.window_should_close(Window):
        tempo_atual = glfw.get_time()
        Tempo_entre_frames = tempo_atual - tempo_anterior
        tempo_anterior = tempo_atual

        glClearColor(0.2, 0.3, 0.3, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        glBindVertexArray(Vao_cubo)

        # -------------------------------------------------------------
        # 1. RENDERIZA OS PONTOS DE CONTROLE
        # Desenhamos cubos estáticos nas posições de P0 a P3 para que os 
        # alunos visualizem as "âncoras" invisíveis que moldam a curva.
        # -------------------------------------------------------------
        defineCor(1.0, 0.0, 0.0, 1.0) # Vermelho
        pontos = [Ponto_Controle_0, Ponto_Controle_1, Ponto_Controle_2, Ponto_Controle_3]
        for p in pontos:
            transformacaoGenerica(p[0], p[1], p[2], 0.5, 0.5, 0.5, 0, 0, 0)
            glDrawArrays(GL_TRIANGLES, 0, 36)

        # -------------------------------------------------------------
        # 2. CÁLCULO DA ANIMAÇÃO PROCEDURAL NO FRAME ATUAL
        # -------------------------------------------------------------
        
        # Garante que 't' varia repetidamente entre 0.0 e 1.0 com base no tempo real
        t = (tempo_atual % duracao_ciclo) / duracao_ciclo
        
        # Calcula onde o objeto deve estar no espaço 3D neste exato milissegundo
        posicao = calculaPosicaoBezierCubica(Ponto_Controle_0, Ponto_Controle_1, Ponto_Controle_2, Ponto_Controle_3, t)
        
        # Calcula para onde a frente do objeto deve apontar
        tangente = calculaTangenteBezierCubica(Ponto_Controle_0, Ponto_Controle_1, Ponto_Controle_2, Ponto_Controle_3, t)
        
        # Converte a direção do vetor tangente em um ângulo de rotação em Y (em graus).
        angulo_ry = np.degrees(np.arctan2(tangente[0], tangente[2]))

        # -------------------------------------------------------------
        # 3. RENDERIZA O OBJETO ANIMADO
        # -------------------------------------------------------------
        defineCor(0.0, 1.0, 0.5, 1.0) # Verde/Ciano
        
        # Aplica a posição calculada e gira o objeto pelo eixo Y para "olhar" para a frente da curva.
        # Escala ajustada em Z (2.0) para que o objeto fique retangular, tornando a rotação visível.
        transformacaoGenerica(posicao[0], posicao[1], posicao[2], 1.0, 1.0, 2.0, 0, angulo_ry, 0)
        glDrawArrays(GL_TRIANGLES, 0, 36)

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

    glfw.terminate()

def defineCor(r, g, b, a):
    cor = np.array([r, g, b, a], dtype=np.float32)
    loc = glGetUniformLocation(Shader_programm, "corobjeto")
    glUniform4fv(loc, 1, cor)

# -----------------------------
# Função principal
# -----------------------------

def main():
    inicializaOpenGL()
    inicializaCubo()
    inicializaShaders()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()