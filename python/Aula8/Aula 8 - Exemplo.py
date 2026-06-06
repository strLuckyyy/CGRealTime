# Câmera e Iluminação - exemplo base para a disciplina de Computação Gráfica em Tempo Real
#
# Este código serve como base para toda a disciplina.
# Ele implementa:
#   - OpenGL moderno (pipeline programável)
#   - Um modelo geométrico simples (cubo) com posições e normais
#   - Transformações de modelo, visualização (câmera) e projeção
#   - Uma câmera no estilo FPS (yaw + pitch)
#   - Iluminação de Phong: ambiente + difuso + especular
#
# A partir deste exemplo, novos conceitos serão adicionados gradualmente
# (materiais, texturas, visibilidade, sombras, etc.)
#
# O modelo de Phong calcula a cor de cada fragmento em função de:
#   - Ka  - coeficiente de luz ambiente  (iluminação mínima global)
#   - Kd  - coeficiente difuso           (espalhamento lambertiano)
#   - Ks  - coeficiente especular        (reflexo brilhante)
#   - shininess - expoente especular     (quanto mais alto, menor e mais nítido o brilho)
#
# Controles:
#   W/A/S/D   - mover câmera (FPS)
#   Mouse     - girar câmera
#   ESC       - fechar

import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import ctypes
import math

# -----------------------------
# Configuração geral
# -----------------------------



Window          = None
Shader_programm = None
Vao_cubo        = None
Vao_esfera      = None
Num_vertices_esfera = 0 # Precisamos guardar a quantidade de vértices gerados

WIDTH  = 800
HEIGHT = 600

# Câmera FPS
Cam_speed = 10.0
Cam_pos   = np.array([0.0, 0.0, 2.0], dtype=np.float32)
Cam_yaw   =  -90.0   # rotação horizontal
Cam_pitch =  0.0   # rotação vertical

lastX, lastY   = WIDTH / 2, HEIGHT / 2
primeiro_mouse = True

Tempo_entre_frames = 0.0  # variável utilizada para movimentar a câmera

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

def key_callback(window, key, scancode, action, mods):
    return
    
# -----------------------------
# Inicialização do OpenGL
# -----------------------------

def inicializaOpenGL():
    global Window

    # Inicializa GLFW
    glfw.init()

    # Criação de uma janela
    Window = glfw.create_window(WIDTH, HEIGHT, 'Câmera e Iluminação - CG em Tempo Real', None, None)
    if not Window:
        glfw.terminate()
        exit()   
    glfw.make_context_current(Window)

    glfw.set_input_mode(Window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_cursor_pos_callback(Window, mouse_callback)
    glfw.set_window_size_callback(Window, redimensionaCallback)
    glfw.set_key_callback(Window, key_callback)

    print("Placa de vídeo: ", glGetString(GL_RENDERER))
    print("Versão do OpenGL: ", glGetString(GL_VERSION))

# -----------------------------
# Inicialização da geometria
# -----------------------------
# Aqui criamos o MODELO geométrico do cubo.
# O cubo é definido uma única vez e pode ser instanciado várias vezes na cena.
#
# Cada vértice carrega dois atributos:
#   - posição (x, y, z)   - location 0
#   - normal  (nx, ny, nz) - location 1
#
# As normais são necessárias para o cálculo de iluminação:
# indicam para qual lado cada face está "olhando", o que determina
# como a luz incide e é espalhada pela superfície.

def inicializaCubo():
    global Vao_cubo

    # Formato por vértice: [x, y, z,  nx, ny, nz]
    # A normal de cada face é constante - efeito "facetado" (flat shading por face)
    pontos = [
        # face frontal (+Z) - normal (0, 0, 1)
         0.5,  0.5,  0.5,   0, 0, 1,
         0.5, -0.5,  0.5,   0, 0, 1,
        -0.5, -0.5,  0.5,   0, 0, 1,
         0.5,  0.5,  0.5,   0, 0, 1,
        -0.5, -0.5,  0.5,   0, 0, 1,
        -0.5,  0.5,  0.5,   0, 0, 1,

        # face traseira (-Z) - normal (0, 0, -1)
         0.5,  0.5, -0.5,   0, 0,-1,
         0.5, -0.5, -0.5,   0, 0,-1,
        -0.5, -0.5, -0.5,   0, 0,-1,
         0.5,  0.5, -0.5,   0, 0,-1,
        -0.5, -0.5, -0.5,   0, 0,-1,
        -0.5,  0.5, -0.5,   0, 0,-1,

        # face esquerda (-X) - normal (-1, 0, 0)
        -0.5, -0.5,  0.5,  -1, 0, 0,
        -0.5,  0.5,  0.5,  -1, 0, 0,
        -0.5, -0.5, -0.5,  -1, 0, 0,
        -0.5, -0.5, -0.5,  -1, 0, 0,
        -0.5,  0.5, -0.5,  -1, 0, 0,
        -0.5,  0.5,  0.5,  -1, 0, 0,

        # face direita (+X) - normal (1, 0, 0)
         0.5, -0.5,  0.5,   1, 0, 0,
         0.5,  0.5,  0.5,   1, 0, 0,
         0.5, -0.5, -0.5,   1, 0, 0,
         0.5, -0.5, -0.5,   1, 0, 0,
         0.5,  0.5, -0.5,   1, 0, 0,
         0.5,  0.5,  0.5,   1, 0, 0,

        # face inferior (-Y) - normal (0, -1, 0)
        -0.5, -0.5,  0.5,   0,-1, 0,
         0.5, -0.5,  0.5,   0,-1, 0,
         0.5, -0.5, -0.5,   0,-1, 0,
         0.5, -0.5, -0.5,   0,-1, 0,
        -0.5, -0.5, -0.5,   0,-1, 0,
        -0.5, -0.5,  0.5,   0,-1, 0,

        # face superior (+Y) - normal (0, 1, 0)
        -0.5,  0.5,  0.5,   0, 1, 0,
         0.5,  0.5,  0.5,   0, 1, 0,
         0.5,  0.5, -0.5,   0, 1, 0,
         0.5,  0.5, -0.5,   0, 1, 0,
        -0.5,  0.5, -0.5,   0, 1, 0,
        -0.5,  0.5,  0.5,   0, 1, 0,
    ]
    pontos = np.array(pontos, dtype=np.float32)

    Vao_cubo = glGenVertexArrays(1)
    glBindVertexArray(Vao_cubo)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, pontos, GL_STATIC_DRAW)

    stride = 6 * 4  # 6 floats × 4 bytes por float

    # Atributo 0: posição (x, y, z)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))

    # Atributo 1: normal (nx, ny, nz) - usada pelo shader para calcular a iluminação
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))

# -----------------------------
# Algoritmo de Geração da Esfera
# -----------------------------
# Aqui calculamos matematicamente os vértices que formam o MODELO da esfera.
# O algoritmo mapeia a superfície esférica dividindo-a em uma grade composta por
# fatias horizontais (stacks/latitude) e fatias verticais (sectors/longitude).
#
# O processo de construção segue 3 etapas principais:
#
# 1. Conversão de Coordenadas:
#    Percorremos os ângulos da esfera usando as fatias. Os ângulos (phi e theta)
#    são convertidos de coordenadas esféricas para coordenadas cartesianas (x, y, z)
#    utilizando as funções trigonométricas de seno e cosseno e o raio desejado.
#
# 2. Triangulação da Superfície:
#    O cruzamento de duas fatias horizontais com duas verticais forma um "quadrado"
#    curvado na superfície. Como placas de vídeo renderizam apenas triângulos, 
#    dividimos cada quadrado em 2 triângulos adjacentes (gerando 6 vértices por iteração).
#
# 3. Cálculo das Normais:
#    Em uma esfera perfeitamente simétrica e centrada na origem (0,0,0), 
#    a direção para a qual a superfície "aponta" é irradiada a partir do centro.
#    Logo, a normal de qualquer vértice é simplesmente a sua própria posição 
#    dividida pelo raio da esfera (para o vetor ficar com tamanho 1).

def inicializaEsfera():
    global Vao_esfera, Num_vertices_esfera
    points = []
    
    # Resolução da esfera (quanto maior, mais redonda, porém mais pesada)
    stacks = 30  # Fatias horizontais (latitude)
    sectors = 30 # Fatias verticais (longitude)
    radius = 0.5
    PI = math.pi

    for i in range(stacks):
        phi1 = PI * i / stacks
        phi2 = PI * (i + 1) / stacks

        for j in range(sectors):
            theta1 = 2.0 * PI * j / sectors
            theta2 = 2.0 * PI * (j + 1) / sectors

            # Função auxiliar para calcular e adicionar um vértice e sua normal
            def add_vertex(p, t):
                # Coordenadas esféricas para cartesianas
                x = radius * math.sin(p) * math.cos(t)
                y = radius * math.cos(p)
                z = radius * math.sin(p) * math.sin(t)

                # 1. Adiciona a Posição
                points.extend([x, y, z])

                # 2. Adiciona a Normal
                points.extend([x / radius, y / radius, z / radius])

            # Um "quadrado" na superfície da esfera é formado por 2 triângulos.
            # Triângulo 1
            add_vertex(phi1, theta1)
            add_vertex(phi2, theta1)
            add_vertex(phi1, theta2)

            # Triângulo 2
            add_vertex(phi1, theta2)
            add_vertex(phi2, theta1)
            add_vertex(phi2, theta2)

    # Calcula quantos vértices reais foram gerados
    Num_vertices_esfera = len(points) // 6

    # Converte a lista do Python para um array do C contíguo na memória usando NumPy
    points_data = np.array(points, dtype=np.float32)

    # Geração dos buffers OpenGL
    Vao_esfera = glGenVertexArrays(1)
    vbo = glGenBuffers(1)

    glBindVertexArray(Vao_esfera)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    
    # Passamos o número de bytes do array (points_data.nbytes) e o próprio array
    glBufferData(GL_ARRAY_BUFFER, points_data.nbytes, points_data, GL_STATIC_DRAW)

    # Tamanho do float em bytes para calcular o stride e os offsets
    float_size = ctypes.sizeof(ctypes.c_float)
    stride = 6 * float_size

    # Atributo 0: Posição
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    # Atributo 1: Normal
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * float_size))
    glEnableVertexAttribArray(1)
    
    # Desvincula o VAO (boa prática)
    glBindVertexArray(0)

def inicializaSuperficie(type = 'sphere'):
    resolucao_u = 30 # Passos longitudinais
    resolucao_v = 30 # Passos transversais
    
    passo_u = 1/resolucao_u
    passo_v = 1/resolucao_v
    largura = resolucao_v + 1
    
    vertices = []
    #GERAÇÃO DE VÉRTICES
    for i in range(resolucao_u + 1):
        u = i * passo_u
        for j in range(resolucao_v + 1):
            v = j * passo_v

            # --- INÍCIO DO BLOCO MATEMÁTICO DA FORMA ---
            # É AQUI que definiremos x, y, z, tx, ty, tz, vx, vy, vz
            # de acordo com o objeto que queremos gerar.

            if type == 'sphere':
                radius = 0.5
                phi = u * math.pi
                theta = -(v * math.pi * 2.0)

                x = radius * math.sin(phi) * math.cos(theta)
                y = radius * math.cos(phi)
                z = radius * math.sin(phi) * math.sin(theta)

                # 3. Tangentes (Derivadas parciais)
                dphi_du = math.pi
                dtheta_dv = -2.0 * math.pi

                # Derivando S em relação a 'u' (Tangente U via phi)
                tx = radius * math.cos(phi) * math.cos(theta) * dphi_du
                ty = -radius * math.sin(phi) * dphi_du
                tz = radius * math.cos(phi) * math.sin(theta) * dphi_du

                # Derivando S em relação a 'v' (Tangente V via theta)
                vx = -radius * math.sin(phi) * math.sin(theta) * dtheta_dv
                vy = 0.0
                vz = radius * math.sin(phi) * math.cos(theta) * dtheta_dv

            elif type == 'surface':
                # Exemplo: TERRENO ONDULADO
                freq = 5.0 # Frequência das montanhas
                amplitude = 0.1 # Altura das montanhas
                tamanho = 200

                # 1. Posição (S(u,v))
                # Centralizamos X e Z entre -0.5 e 0.5
                x = (u - 0.5) * tamanho
                z = (0.5 - v) * tamanho

                # A altura Y é uma onda composta
                y = amplitude * math.sin(u * freq) * math.cos(v * freq) * tamanho

                # 3. Tangentes (Derivadas parciais)
                # Derivando a altura Y em relação a 'u' e 'v'
                dy_du = amplitude * freq * math.cos(u * freq) * math.cos(v * freq)
                dy_dv = -amplitude * freq * math.sin(u * freq) * math.sin(v * freq)

                # Tangente U (derivadas de x, y, z em relação a u)
                tx = 1.0
                ty = dy_du
                tz = 0.0

                # Tangente V (derivadas de x, y, z em relação a v)
                vx = 0.0
                vy = dy_dv
                vz = -1.0

            # --- FIM DO BLOCO MATEMÁTICO DA FORMA ---
            # Produto vetorial das tangentes para obter a Normal

            Tu = np.array([tx, ty, tz])
            Tv = np.array([vx, vy, vz])
            N = np.cross(Tu, Tv)

            # Normalização (evitando divisão por zero)
            norma = np.linalg.norm(N)
            if norma != 0:
                N = N / norma
            
             # Empacotamento dos 11 floats do vértice atual
            vertices.extend([
                x, y, z, # Offset 0: Posição
                N[0], N[1], N[2], # Offset 12: Normal procedural
                u, v, # Offset 24: Coordenadas UV
                tx, ty, tz # Offset 32: Tangente U
            ])

    indices = []
    for i in range(resolucao_u):
        for j in range(resolucao_v):
            # Índices lineares da célula atual
            sup_esq = i * largura + j
            sup_dir = sup_esq + 1
            inf_esq = (i + 1) * largura + j
            inf_dir = inf_esq + 1
            # Geração dos dois triângulos (sentido anti-horário)
            indices.extend([sup_esq, inf_esq, sup_dir])
            indices.extend([sup_dir, inf_esq, inf_dir])

    Num_indices_geometria = len(indices)

    vertices_data = np.array(vertices, dtype=np.float32)
    indices_data = np.array(indices, dtype=np.uint32)

    Vao_geometria = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    ebo = glGenBuffers(1)

    glBindVertexArray(Vao_geometria)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices_data.nbytes, vertices_data, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices_data.nbytes, indices_data, GL_STATIC_DRAW)

    # Definição do layout de memória. Cada vértice tem 11 floats (44 bytes)
    float_size = ctypes.sizeof(ctypes.c_float)
    stride = 11 * float_size

    # Atributo 0: Posição (3 floats)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    # Atributo 1: Normal (3 floats, começa após os 3 primeiros floats)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * float_size))
    glEnableVertexAttribArray(1)

    # Atributo 2: Coordenadas UV (2 floats, começa após 6 floats)
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(6 * float_size))
    glEnableVertexAttribArray(2)

    # Atributo 3: Tangente U (3 floats, começa após 8 floats)
    glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8 * float_size))
    glEnableVertexAttribArray(3)

    glBindVertexArray(0)

    return Vao_geometria, Num_indices_geometria




# -----------------------------
# Shaders
# -----------------------------
# O vertex shader transforma a posição do vértice e propaga a normal
# para o espaço do mundo, onde a iluminação será calculada.
#
# O fragment shader implementa o modelo de iluminação de Phong:
#   - Ambiente:  Ka × lightColor
#   - Difuso:    Kd × max(dot(N, L), 0) × lightColor
#   - Especular: Ks × max(dot(N, H), 0)^shininess × lightColor
#
# onde:
#   N = normal do fragmento (normalizada)
#   L = direção da luz      (do fragmento para a luz)
#   V = direção da câmera   (do fragmento para a câmera)
#   H = half-vector         (bissetriz entre L e V - modelo de Blinn-Phong)

def inicializaShaders():
    global Shader_programm

    # Especificação do Vertex Shader:
    vertex_shader = """
        #version 450
        layout(location = 0) in vec3 vertex_posicao;
        layout(location = 1) in vec3 vertex_normal;

        // transform - matriz de modelo recebida do Python
        // view      - matriz da câmera recebida do Python
        // proj      - matriz de projeção recebida do Python
        uniform mat4 transform, view, proj;

        out vec3 fragPos;   // posição do fragmento no espaço do mundo
        out vec3 normal;    // normal transformada para o espaço do mundo

        void main() {
            vec4 worldPos = transform * vec4(vertex_posicao, 1.0);
            fragPos = worldPos.xyz;

            // Transforma a normal usando a inversa transposta da matriz de modelo.
            // Isso é necessário para que escala não-uniforme não distorça as normais.
            normal = mat3(transpose(inverse(transform))) * vertex_normal;

            gl_Position = proj * view * worldPos;
        }
    """

    # Especificação do Fragment Shader:
    fragment_shader = """
        #version 400
        
        in vec3 fragPos;
        in vec3 normal;

        out vec4 frag_colour;

        uniform vec3 lightPos;    // posição da fonte de luz no mundo
        uniform vec3 viewPos;     // posição da câmera no mundo

        uniform vec3 lightColor;  // cor/intensidade da luz
        uniform vec3 objectColor; // cor base do objeto (albedo)

        // Coeficientes do modelo de Phong
        uniform float Ka;         // fração de luz ambiente
        uniform float Kd;         // fração de luz difusa
        uniform float Ks;         // fração de luz especular
        uniform float shininess;  // expoente especular (brilho)
        
        // Constantes da equação de atenuação
        uniform float Kc; // Constante
        uniform float Kl; // Linear
        uniform float Kq; // Quadrática

        void main() {
            vec3 N = normalize(normal);
            vec3 L = normalize(lightPos - fragPos);
            vec3 V = normalize(viewPos - fragPos);
            vec3 R = normalize(reflect(-L,N)); //Para o modelo de Phong  Tradicional
            //vec3 H = normalize(L + V); //Para o modelo Blinn-Phong

            // 1. Componente ambiente: iluminação mínima global (evita sombras completamente pretas)
            vec3 ambient = Ka * lightColor;

            // 2. Componente difusa: espalhamento lambertiano proporcional ao ângulo com a luz
            float diff = max(dot(N, L), 0.0);
            vec3 diffuse = Kd * diff * lightColor;

            // 3. Componente especular: reflexo brilhante dependente do ângulo com a câmera
            // Opção 1 - Phong Tradicional
            float spec = pow(max(dot(V, R), 0.0), shininess);
            // Opção 2 - Blinn-Phong
            //float spec = pow(max(dot(N, H), 0.0), shininess);
            
            vec3 specular = Ks * spec * lightColor;

            // 4. Aplica a atenuação na difusa (e na especular)
            // Calcula a distância (d) entre a luz e o fragmento
            //float d = length(lightPos - fragPos);

            // Calcula o fator de atenuação (F_att)
            //float attenuation = 1.0 / (Kc + Kl * d + Kq * (d * d));
            //diffuse  *= attenuation;
            //specular *= attenuation;

            // Calcula o modelo de Phong completo
            vec3 result = (ambient + diffuse ) * objectColor + specular;
            frag_colour = vec4(result, 1.0);
        }
    """

    vs = OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
    if not glGetShaderiv(vs, GL_COMPILE_STATUS):
        print("Erro no vertex shader:\n", glGetShaderInfoLog(vs, 512, None))

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
# Define a INSTÂNCIA do modelo no mundo:
# onde ele está, em que escala e com qual rotação.

def transformacaoGenerica(Tx, Ty, Tz, Sx, Sy, Sz, Rx, Ry, Rz):
    # matriz de translação
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

    # combinação das 3 rotações
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
# Definição de material
# -----------------------------

def defineMaterial(r, g, b, ka, kd, ks, shininess):
    """
    Configura os parâmetros de material do objeto no shader de Phong.

    Parâmetros:
      r, g, b    - cor base do objeto (albedo)
      ka         - coeficiente de luz ambiente  (0 = sem ambiente, 1 = máximo)
      kd         - coeficiente difuso           (0 = opaco/mate, 1 = máximo)
      ks         - coeficiente especular        (0 = sem brilho,  1 = máximo)
      shininess  - expoente especular           (valores altos = brilho menor e mais nítido)

    Exemplos típicos:
      Plástico fosco:  ka=0.1, kd=0.8, ks=0.1, shininess=8
      Plástico brilh.: ka=0.1, kd=0.6, ks=0.8, shininess=64
      Metal polido:    ka=0.05, kd=0.3, ks=1.0, shininess=256
    """
    glUniform3f(glGetUniformLocation(Shader_programm, "objectColor"), r, g, b)
    glUniform1f(glGetUniformLocation(Shader_programm, "Ka"),          ka)
    glUniform1f(glGetUniformLocation(Shader_programm, "Kd"),          kd)
    glUniform1f(glGetUniformLocation(Shader_programm, "Ks"),          ks)
    glUniform1f(glGetUniformLocation(Shader_programm, "shininess"),   shininess)

# -----------------------------
# Entrada de teclado
# -----------------------------

def trataTeclado():
    """
    Movimenta a câmera no espaço 3D conforme as teclas WASD.
    A direção do movimento segue o vetor 'frente' (para onde o jogador está
    olhando), incluindo a inclinação vertical (pitch).
    """
    global Cam_pos

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

# -----------------------------
# Loop de renderização
# -----------------------------

def inicializaRenderizacao():
    global Tempo_entre_frames

    tempo_anterior = glfw.get_time()

    # Ativa o teste de profundidade para que faces mais próximas sobreponham as mais distantes
    glEnable(GL_DEPTH_TEST)

    # Luz posicionada fixa no espaço do mundo
    lightPos = np.array([2.0, 2.0, 2.0], dtype=np.float32)

    Vao_Geometria, Num_indices_geometria = inicializaSuperficie(type='surface')

    while not glfw.window_should_close(Window):
        # Calcula quantos segundos se passaram entre um frame e outro
        tempo_atual        = glfw.get_time()
        Tempo_entre_frames = tempo_atual - tempo_anterior
        tempo_anterior     = tempo_atual

        glClearColor(0.2, 0.3, 0.3, 1.0)  # define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # limpa os buffers de cor e profundidade
        glViewport(0, 0, WIDTH, HEIGHT)

        glUseProgram(Shader_programm)
        inicializaCamera()

        

        # Envia a posição da luz e da câmera para o shader (necessárias para Phong)
        glUniform3fv(glGetUniformLocation(Shader_programm, "lightPos"), 1, lightPos)
        glUniform3fv(glGetUniformLocation(Shader_programm, "viewPos"),  1, Cam_pos)

        # Luz branca pura
        glUniform3f(glGetUniformLocation(Shader_programm, "lightColor"), 1.0, 1.0, 1.0)
        
        # Configuração da Atenuação ---
        # Estes valores representam uma luz que cobre uma distância de cerca de 50 unidades.
        # Você pode ajustá-los para fazer a luz ir mais ou menos longe.
        glUniform1f(glGetUniformLocation(Shader_programm, "Kc"), 1.0);   # Constante
        glUniform1f(glGetUniformLocation(Shader_programm, "Kl"), 0.09);  # Linear
        glUniform1f(glGetUniformLocation(Shader_programm, "Kq"), 0.032); # Quadrática

        # Definição de material: laranja com brilho moderado
        defineMaterial(
            1.0, 0.6, 0.2,  # cor base (laranja)
            0.1,            # Ka - pouca luz ambiente
            0.7,            # Kd - difuso predominante
            0.5,            # Ks - brilho moderado
            32.0            # shininess - brilho médio
        )
        
        #Desenha o Cubo
        glBindVertexArray(Vao_Geometria)
        transformacaoGenerica(0.0, 0.0, 0.0,  1.0, 1.0, 1.0,  0, 0, 0)
        glDrawElements(GL_TRIANGLES, Num_indices_geometria, GL_UNSIGNED_INT, None)

        glfw.swap_buffers(Window)
        glfw.poll_events()
        trataTeclado()

    glfw.terminate()

# Função principal
def main():
    inicializaOpenGL()
    inicializaCubo()
    inicializaEsfera()
    inicializaShaders()
    inicializaRenderizacao()

if __name__ == "__main__":
    main()