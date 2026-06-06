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
# - Geração procedural de geometria (Pista de Corrida) utilizando Curvas de Bézier Cúbicas.
# - Cálculo da posição P(t) e do vetor Tangente P'(t) para alinhamento dos blocos.

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

Cam_speed = 15.0          # velocidade de deslocamento da câmera
Cam_yaw_speed = 30.0      # velocidade de rotação horizontal
# Posição inicial ajustada para visualizar a pista de cima/trás
Cam_pos = np.array([0.0, 10.0, -10.0])  
Cam_yaw = 90.0             # rotação horizontal
Cam_pitch = -20.0         # rotação vertical (olhando levemente para baixo)

lastX, lastY = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

# -----------------------------
# Variáveis da Pista de Corrida (Bézier)
# -----------------------------

# Pontos de controle da curva cúbica de Bézier (P0, P1, P2, P3)
# Posicionados no plano XZ (Y = 0) para formar um "S" longo.
Ponto_Controle_0 = np.array([ 0.0, 0.0,  0.0])
Ponto_Controle_1 = np.array([ 30.0, 0.0, 20.0])
Ponto_Controle_2 = np.array([-30.0, 0.0, 40.0])
Ponto_Controle_3 = np.array([ 0.0, 0.0, 60.0])

# Lista que armazenará os dados calculados da pista: (posicao_xyz, angulo_ry)
Dados_Pista = []

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

    Window = glfw.create_window(WIDTH, HEIGHT, "Modelagem com Bezier - Pista de Corrida", None, None)
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
    P(t) = (1-t)^3*P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3*P3
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
    
    A derivada mede a taxa de variação de uma função. Em uma curva 3D, a derivada 
    resulta na reta tangente, ou seja, o vetor que indica a direção exata para onde 
    a curva está apontando naquele valor específico de 't'.
    
    Na aula teórica, foi apresentada a equação da posição da curva cúbica:
    P(t) = (1-t)³*P0 + 3*(1-t)²*t*P1 + 3*(1-t)*t²*P2 + t³*P3
    
    Para encontrar a equação da direção (a derivada P'(t)), aplicamos a regra 
    básica de derivação de polinômios em relação a 't', onde o expoente multiplica 
    a base e é reduzido em 1 (ex: a derivada de t³ vira 3t²). 
    
    Ao derivar todos os termos da equação original P(t) e realizar o agrupamento 
    algébrico, os pontos de controle se unem formando vetores de subtração: 
    (P1 - P0), (P2 - P1) e (P3 - P2). 
    
    A fatoração final dessa derivada resulta exatamente na equação implementada:
    P'(t) = 3(1-t)²*(P1 - P0) + 6(1-t)t*(P2 - P1) + 3t²*(P3 - P2)
    
    Na prática, a fórmula distribui pesos sobre essas três direções com base em 't':
    - Se t = 0 (início), a equação anula as duas últimas partes e sobra 3*(P1 - P0). A curva obrigatoriamente "sai" apontando para P1.
    - Se t = 1 (fim), sobra apenas 3*(P3 - P2). A curva obrigatoriamente "chega" em P3 apontando a partir de P2.
    - Valores intermediários de 't' geram uma mistura (interpolação) dessas direções.
    
    Aplicação: Usamos esse vetor tangente para descobrir o ângulo exato em que devemos 
    rotacionar o nosso modelo 3D. Isso garante que cada pedaço gerado acompanhe o 
    fluxo e a inclinação geométrica do traçado.
    """
    u = 1.0 - t
    uu = u * u
    tt = t * t

    # Calculamos a derivada distribuindo os pesos sobre os vetores de diferença
    tangente = 3 * uu * (p1 - p0)           # Influência da direção inicial
    tangente += 6 * u * t * (p2 - p1)       # Influência da direção central
    tangente += 3 * tt * (p3 - p2)          # Influência da direção final
    
    # Normalizamos o vetor (dividimos pelo seu próprio comprimento para que o tamanho passe a ser 1).
    # Isso garante que a variável armazene puramente a informação de direção, sem distorcer cálculos futuros.
    norma = np.linalg.norm(tangente)
    if norma > 0:
        tangente = tangente / norma
        
    return tangente

def inicializaPista():
    """
    Pré-calcula a geometria da pista de corrida discretizando o parâmetro 't'.
    A discretização transforma a equação contínua em segmentos rasterizáveis.
    """
    global Dados_Pista
    
    numero_de_segmentos = 60 # Equivalente à resolução/precisão da curva
    
    for i in range(numero_de_segmentos + 1):
        # Varia t de 0.0 até 1.0
        t = i / float(numero_de_segmentos)
        
        # 1. Calcula a coordenada exata no espaço 3D
        posicao = calculaPosicaoBezierCubica(Ponto_Controle_0, Ponto_Controle_1, Ponto_Controle_2, Ponto_Controle_3, t)
        
        # 2. Calcula o vetor direção para alinhar o bloco
        tangente = calculaTangenteBezierCubica(Ponto_Controle_0, Ponto_Controle_1, Ponto_Controle_2, Ponto_Controle_3, t)
        
        # 3. Converte a direção do vetor tangente em um ângulo de Rotação em Y (Ry)
        # O arctan2(X, Z) nos dá o ângulo no plano horizontal. 
        # Multiplicamos por radianos para graus, pois nossa função transformacaoGenerica usa graus.
        angulo_ry = np.degrees(np.arctan2(tangente[0], tangente[2]))
        
        Dados_Pista.append((posicao, angulo_ry))

# -----------------------------
# Inicialização da geometria (Cubo)
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
    znear, zfar = 0.1, 1000.0 # Zfar expandido para ver o fim da pista
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

        glClearColor(0.5, 0.7, 1.0, 1.0) # Cor de "Céu"
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        glBindVertexArray(Vao_cubo)

        # 1. RENDERIZAÇÃO DA PISTA
        defineCor(0.2, 0.2, 0.2, 1.0) # Cinza escuro (asfalto)
        
        for dados in Dados_Pista:
            posicao = dados[0]
            angulo_ry = dados[1]
            
            # Tx, Ty, Tz mapeados para a coordenada calculada (posicao)
            # Sx = 8.0 (largura da pista), Sy = 0.2 (achatado), Sz = 1.5 (comprimento do bloco)
            # Ry = angulo_ry para rotacionar o bloco acompanhando a curva
            transformacaoGenerica(posicao[0], posicao[1], posicao[2], 
                                  8.0, 0.2, 1.5, 
                                  0.0, angulo_ry, 0.0)
            glDrawArrays(GL_TRIANGLES, 0, 36)

        # 2. RENDERIZAÇÃO DOS PONTOS DE CONTROLE (Visualização Didática)
        # Mostra as "âncoras" que puxam a curva para sua forma final.
        defineCor(1.0, 0.0, 0.0, 1.0) # Vermelho
        
        pontos_controle = [Ponto_Controle_0, Ponto_Controle_1, Ponto_Controle_2, Ponto_Controle_3]
        for pc in pontos_controle:
            # Desenhados como cubos fixos, menores, e não rotacionados
            transformacaoGenerica(pc[0], pc[1], pc[2], 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
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
    inicializaPista() # Executa a discretização geométrica paramétrica antes do render
    inicializaShaders()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()