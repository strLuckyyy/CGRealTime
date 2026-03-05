# Câmera

# Neste exemplo, especificamos uma câmera virtual através da aplicação de transformações de projeção
import glfw
from OpenGL.GL import *
from dataclasses import dataclass
import OpenGL.GL.shaders
import numpy as np

# Cube Database #
@dataclass
class Cube:
    pos: np.ndarray
    color: np.ndarray
    rot: np.ndarray
    rotAnimacao: bool = False
    transAnimacao: bool = False
    tz: float = 0.0
    direction: int = 1

cubes = [
    Cube(
        pos=np.array([0.0, 0.0, 0.0]),
        color=np.array([1.0, 0.0, 0.0, 1.0]),
        rot=np.array([0.0, 0.0, 0.0])
    ),
    Cube(
        pos=np.array([1.0, 1.0, 1.0]),
        color=np.array([1.0, 1.0, 0.0, 1.0]),
        rot=np.array([0.0, 0.0, 0.0]),
        rotAnimacao=True
    ),
    Cube(
        pos=np.array([2.0, -1.0, 0.0]),
        color=np.array([1.0, 0.0, 1.0, 1.0]),
        rot=np.array([0.0, 0.0, 0.0]),
        transAnimacao=True
    )
]
# End Cube Database #

Window = None
Shader_programm = None
Vao_cubo = None
WIDTH = 800
HEIGHT = 600

Tempo_entre_frames = 0 #variavel utilizada para movimentar a camera

#Variáveis referentes a câmera virtual e sua projeção

Cam_speed = 10.0 #velocidade da camera, 10 unidade por segundo
Cam_pos = np.array([0.0, 0.0, 2.0]) #posicao inicial da câmera
Cam_yaw = 0.0 #ângulo de rotação da câmera em y
Cam_pitch = 0.0  # controle vertical
lastX, lastY = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

canRot = True
rot = 0
S = 1

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
    
def inicializaOpenGL():
    global Window, WIDTH, HEIGHT

    #Inicializa GLFW
    glfw.init()

    #Criação de uma janela
    Window = glfw.create_window(WIDTH, HEIGHT, "Exemplo - Cubo 3D", None, None)
    if not Window:
        glfw.terminate()
        exit()

    glfw.set_window_size_callback(Window, redimensionaCallback)
    glfw.make_context_current(Window)
    
    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)
    glfw.set_key_callback(Window, key_callback)

    print("Placa de vídeo: ",OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER))
    print("Versão do OpenGL: ",OpenGL.GL.glGetString(OpenGL.GL.GL_VERSION))

def inicializaCubo():
    global Vao_cubo
    # Vao do cubo
    Vao_cubo = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo)

    # VBO dos vértices do quadrado (36 vértices)
    points = [
		#face frontal
		0.5, 0.5, 0.5,#0
		0.5, -0.5, 0.5,#1
		-0.5, -0.5, 0.5,#2
		-0.5, 0.5, 0.5,#3
		0.5, 0.5, 0.5,
		-0.5, -0.5, 0.5,
		#face trazeira
		0.5, 0.5, -0.5,#4
		0.5, -0.5, -0.5,#5
		-0.5, -0.5, -0.5,#6
		-0.5, 0.5, -0.5,#7
		0.5, 0.5, -0.5,
		-0.5, -0.5, -0.5,
		#face esquerda
		-0.5, -0.5, 0.5,
		-0.5, 0.5, 0.5,
		-0.5, -0.5, -0.5,
		-0.5, -0.5, -0.5,
		-0.5, 0.5, -0.5,
		-0.5, 0.5, 0.5,
		#face direita
		0.5, -0.5, 0.5,
		0.5, 0.5, 0.5,
		0.5, -0.5, -0.5,
		0.5, -0.5, -0.5,
		0.5, 0.5, -0.5,
		0.5, 0.5, 0.5,
		#face baixo
		-0.5, -0.5, 0.5,
		0.5, -0.5, 0.5,
		0.5, -0.5, -0.5,
		0.5, -0.5, -0.5,
		-0.5, -0.5, -0.5,
		-0.5, -0.5, 0.5,
		#face cima
		-0.5, 0.5, 0.5,
		0.5, 0.5, 0.5,
		0.5, 0.5, -0.5,
		0.5, 0.5, -0.5,
		-0.5, 0.5, -0.5,
		-0.5, 0.5, 0.5,
	]

    points = np.array(points, dtype=np.float32)
    pvbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, pvbo)
    glBufferData(GL_ARRAY_BUFFER, points, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

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
            gl_Position = proj*view*transform*vec4 (vertex_posicao, 1.0);
        }
    """
    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    if not glGetShaderiv(vs, GL_COMPILE_STATUS):
        infoLog = glGetShaderInfoLog(vs, 512, None)
        print("Erro no vertex shader:\n", infoLog)

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
        infoLog = glGetShaderInfoLog(fs, 512, None)
        print("Erro no fragment shader:\n", infoLog)

    # Especificação do Shader Programm:
    Shader_programm = OpenGL.GL.shaders.compileProgram(vs, fs)
    if not glGetProgramiv(Shader_programm, GL_LINK_STATUS):
        infoLog = glGetProgramInfoLog(Shader_programm, 512, None)
        print("Erro na linkagem do shader:\n", infoLog)

    glDeleteShader(vs)
    glDeleteShader(fs)

def transformacaoGenerica(Tx, Ty, Tz, Sx, Sy, Sz, Rx, Ry, Rz):
    #matriz de translação
    translacao = np.array([
        [1.0, 0.0, 0.0, Tx], 
        [0.0, 1.0, 0.0, Ty], 
        [0.0, 0.0, 1.0, Tz], 
        [0.0, 0.0, 0.0, 1.0]], np.float32)

    #matriz de rotação em torno do eixo X
    angulo = np.radians(Rx)
    cos, sen = np.cos(angulo), np.sin(angulo)
    rotacaoX = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, cos, -sen, 0.0],
        [0.0, sen, cos, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])

    #matriz de rotação em torno do eixo Y
    angulo = np.radians(Ry)
    cos, sen = np.cos(angulo), np.sin(angulo)
    rotacaoY = np.array([
        [cos, 0.0, sen, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-sen, 0.0, cos, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])

    #matriz de rotação em torno do eixo Z
    angulo = np.radians(Rz)
    cos, sen = np.cos(angulo), np.sin(angulo)
    rotacaoZ = np.array([
        [cos, -sen, 0.0, 0.0],
        [sen, cos, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])

    #combinação das 3 rotação
    rotacao = rotacaoZ.dot(rotacaoY.dot(rotacaoX))

    #matriz de escala
    escala = np.array([
        [Sx, 0.0, 0.0, 0.0], 
        [0.0, Sy, 0.0, 0.0], 
        [0.0, 0.0, Sz, 0.0], 
        [0.0, 0.0, 0.0, 1.0]], np.float32)

    transformacaoFinal = translacao.dot(rotacao.dot(escala))
    
    #E passamos a matriz para o Vertex Shader.
    transformLoc = glGetUniformLocation(Shader_programm, "transform")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, transformacaoFinal)

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
        ->o que está “na frente” da câmera é trazido para o eixo -Z,
        ->o “lado direito” para o +X e o “cima” para o +Y, como no sistema de visão padrão do OpenGL.

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
    view[2, 3] = np.dot(f, Cam_pos)

    transformLoc = glGetUniformLocation(Shader_programm, "view")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, view)

def especificaMatrizProjecao():
    #Especificação da matriz de projeção perspectiva.
    znear = 0.1 #recorte z-near
    zfar = 100.0 #recorte z-far
    fov = np.radians(67.0) #campo de visão
    aspecto = WIDTH/HEIGHT #aspecto

    a = 1/(np.tan(fov/2)*aspecto)
    b = 1/(np.tan(fov/2))
    c = (zfar + znear) / (znear - zfar)
    d = (2*znear*zfar) / (znear - zfar)
    projecao = np.array([
        [a,   0.0, 0.0,  0.0],
        [0.0, b,   0.0,  0.0],
        [0.0, 0.0, c,    d],
        [0.0, 0.0, -1.0, 1.0]
    ])

    transformLoc = glGetUniformLocation(Shader_programm, "proj")
    glUniformMatrix4fv(transformLoc, 1, GL_TRUE, projecao)

def inicializaCamera():
    especificaMatrizVisualizacao() #posição da câmera e orientação da câmera (rotação)
    especificaMatrizProjecao() #perspectiva ou paralela

def trataTeclado():
    """
    Movimenta a câmera no espaço 3D conforme teclas WASD.
    A direção do movimento segue o vetor 'front' (para onde o jogador está olhando),
    incluindo a inclinação vertical (pitch), assim o movimento é fiel ao olhar.
    """
    global Cam_pos, Cam_yaw, Cam_pitch, Tempo_entre_frames, canRot, S

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

    # Size #
    if glfw.get_key(Window, glfw.KEY_UP) == glfw.PRESS: 
        S += .05
    if glfw.get_key(Window, glfw.KEY_DOWN) == glfw.PRESS: 
        S -= .05

    if S < 0.1: S = 0.1
    if S > 3: S = 3
    # End Size #

    # Can Rotate #
    if glfw.get_key(Window, glfw.KEY_1) == glfw.PRESS: canRot = False
    if glfw.get_key(Window, glfw.KEY_2) == glfw.PRESS: canRot = True
    # End Can Rotate #
 
def defineCor(r, g, b, a):
    #array de cores que vamos mandar pro shader
    cores = np.array([r, g, b, a]) 
    #buscou a localização na memória de video da variável corobjeto
    coresLoc = glGetUniformLocation(Shader_programm, "corobjeto")
    #passa os valores do vetor de cores aqui do python para o shader
    glUniform4fv(coresLoc, 1, cores)
    
def inicializaRenderizacao():
    global Window, Shader_programm, Vao_cubo, WIDTH, HEIGHT, Tempo_entre_frames, S, rot, canRot

    tempo_anterior = glfw.get_time()

    #Ativação do teste de profundidade. Sem ele, o OpenGL não sabe que faces devem ficar na frente e que faces devem ficar atrás.
    glEnable(GL_DEPTH_TEST)
    #Ativa misutra de cores, para podermos usar transparência
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    trans = 5
    distancia = 3

    while not glfw.window_should_close(Window):
        #calcula quantos segundos se passaram entre um frame e outro
        tempo_frame_atual = glfw.get_time()
        Tempo_entre_frames = tempo_frame_atual - tempo_anterior
        tempo_anterior = tempo_frame_atual

        glClearColor(0.2, 0.3, 0.3, 1.0) #define a cor do fundo da tela com uma cor meio acinzentada
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) #limpa o buffer de cores e de profundidade
        
        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)

        inicializaCamera()

        glBindVertexArray(Vao_cubo) # modelo do cubo; iniciando antes do loop para todos terem o mesmo VAO   

        for i in cubes:
            # CUBO RODANDO (CUBO 2)
            if i.rotAnimacao and canRot:
                i.rot[0] += 80 * Tempo_entre_frames
                if i.rot[0] >= 360: i.rot[0] = 0

            # CUBO MOVENDO (CUBO 3)
            if i.transAnimacao:
                if i.tz >= distancia: i.direction = -1
                if i.tz <= -distancia: i.direction = 1

                i.tz += i.direction * trans * Tempo_entre_frames

            defineCor(i.color[0], i.color[1], i.color[2], i.color[3])

            transformacaoGenerica(
                i.pos[0], i.pos[1], i.pos[2] + i.tz, 
                S, S, S, 
                i.rot[0], i.rot[1], i.rot[2])
            
            glDrawArrays(GL_TRIANGLES, 0, 36)


        glfw.poll_events()
        glfw.swap_buffers(Window)
        
        trataTeclado()

    glfw.terminate()

# Função principal
def main():
    inicializaOpenGL()
    inicializaCubo()
    inicializaShaders()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()