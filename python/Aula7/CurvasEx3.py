# Câmera e exemplo base para a disciplina de Computação Gráfica em Tempo Real e Computação Gráfica Avançada
#
# ADIÇÃO:
# - GPU Instancing guiado por Curva de Bézier Cúbica.
# - Uma única chamada de desenho (glDrawArraysInstanced) gera múltiplos objetos.
# - A GPU avalia a curva e reposiciona os vértices do modelo base em tempo real.
# - Câmera FPS completa (mouse e teclado) preservada.

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
# Posição inicial ajustada para enquadrar a curva gerada
Cam_pos = np.array([0.0, 15.0, -25.0])  
Cam_yaw = 90.0             # rotação horizontal
Cam_pitch = -25.0         # rotação vertical

lastX, lastY = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# -----------------------------
# Variáveis da Curva (Bézier)
# -----------------------------
Ponto_Controle_0 = np.array([-15.0,  0.0,   0.0], dtype=np.float32)
Ponto_Controle_1 = np.array([ -5.0,  0.0,  20.0], dtype=np.float32)
Ponto_Controle_2 = np.array([  5.0,  0.0,  20.0], dtype=np.float32)
Ponto_Controle_3 = np.array([ 15.0,  0.0,   0.0], dtype=np.float32)

Quantidade_Objetos = 100 # Desenhar 100 cubos simultaneamente

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

    Window = glfw.create_window(WIDTH, HEIGHT, "GPU Instancing com Bézier e Câmera FPS", None, None)
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
# Inicialização da geometria (Cubo Base)
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
# Shaders (Processamento Massivo na GPU)
# -----------------------------
def inicializaShaders():
    global Shader_programm

    vertex_shader = """
        #version 400
        layout(location = 0) in vec3 vertex_posicao;

        uniform int num_instancias;
        uniform vec3 p0;
        uniform vec3 p1;
        uniform vec3 p2;
        uniform vec3 p3;

        uniform mat4 view;
        uniform mat4 proj;

        void main() {
            // 1. DESCOBRE QUEM SOU EU
            // gl_InstanceID identifica qual cópia do objeto está sendo processada.
            // Transforma o ID no parâmetro 't' normalizado (0.0 a 1.0).
            float t = float(gl_InstanceID) / float(num_instancias - 1);
            
            // 2. EQUAÇÃO DE BÉZIER (Avaliação Espacial)
            float u = 1.0 - t;
            float tt = t * t;
            float uu = u * u;
            float uuu = uu * u;
            float ttt = tt * t;

            vec3 posicao_na_curva = (uuu * p0) + (3.0 * uu * t * p1) + (3.0 * u * tt * p2) + (ttt * p3);

            // 3. TRANSFORMAÇÃO DO MODELO
            // Escala local do cubo base (para virar um bloco menor) e translação para a curva
            vec3 cubo_escalado = vertex_posicao * 0.5;
            vec3 posicao_final_mundo = cubo_escalado + posicao_na_curva;

            // 4. PROJEÇÃO DE CÂMERA
            gl_Position = proj * view * vec4(posicao_final_mundo, 1.0);
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
# Câmera e Matrizes
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
# Renderização
# -----------------------------
def inicializaRenderizacao():
    global Tempo_entre_frames

    tempo_anterior = glfw.get_time()

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

        # Envio dos Uniforms da curva
        glUniform1i(glGetUniformLocation(Shader_programm, "num_instancias"), Quantidade_Objetos)
        glUniform3fv(glGetUniformLocation(Shader_programm, "p0"), 1, Ponto_Controle_0)
        glUniform3fv(glGetUniformLocation(Shader_programm, "p1"), 1, Ponto_Controle_1)
        glUniform3fv(glGetUniformLocation(Shader_programm, "p2"), 1, Ponto_Controle_2)
        glUniform3fv(glGetUniformLocation(Shader_programm, "p3"), 1, Ponto_Controle_3)

        defineCor(1.0, 0.5, 0.0, 1.0) # Laranja

        glBindVertexArray(Vao_cubo)

        # O PONTO CHAVE DA APLICAÇÃO:
        # A instrução Instanced roda a geometria do VAO repetidas vezes de forma hiperotimizada.
        glDrawArraysInstanced(GL_TRIANGLES, 0, 36, Quantidade_Objetos)

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

    glfw.terminate()

def defineCor(r, g, b, a):
    cor = np.array([r, g, b, a], dtype=np.float32)
    loc = glGetUniformLocation(Shader_programm, "corobjeto")
    glUniform4fv(loc, 1, cor)

def main():
    inicializaOpenGL()
    inicializaCubo() 
    inicializaShaders()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()