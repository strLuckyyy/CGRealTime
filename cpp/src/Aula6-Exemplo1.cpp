// Câmera e Iluminação básica
//
// Este código serve como base para Iluminação local.
// Ele implementa:
// - OpenGL moderno (pipeline programável)
// - Um modelo geométrico simples (cubo)
// - Transformações de modelo, visualização (câmera) e projeção
// - Uma câmera no estilo FPS (yaw + pitch)
// - Iluminação de Phong: ambiente + difuso + especular
// O modelo de Phong calcula a cor de cada fragmento em função de:
//   - Ka  — coeficiente de luz ambiente  (iluminação mínima global)
//   - Kd  — coeficiente difuso           (espalhamento lambertiano)
//   - Ks  — coeficiente especular        (reflexo brilhante)
//   - shininess — expoente especular     (quanto mais alto, menor e mais nítido o brilho)
//
// Controles:
//   W/A/S/D   — mover câmera (FPS)
//   Mouse     — girar câmera
//   ESC       — fechar

#include <iostream>
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>
#include <vector>
#include <cmath>

using namespace std;

// -----------------------------
// Configuração geral
// -----------------------------

GLFWwindow *Window = nullptr;
GLuint Shader_programm = 0;
GLuint Vao_cubo = 0;
GLuint Vao_esfera = 0;
int Num_vertices_esfera = 0; // Precisamos guardar a quantidade de vértices gerados

int WIDTH = 800;
int HEIGHT = 600;



// Câmera FPS
float Cam_speed = 10.0f;
glm::vec3 Cam_pos(0.0f, 0.0f, 2.0f);
float Cam_yaw = -90.0f;
float Cam_pitch = 0.0f;

double lastX = WIDTH / 2.0;
double lastY = HEIGHT / 2.0;
bool primeiro_mouse = true;

float Tempo_entre_frames = 0.0f;

// -----------------------------
// Callbacks de janela e entrada
// -----------------------------

void redimensionaCallback(GLFWwindow *window, int w, int h)
{
    WIDTH = w;
    HEIGHT = h;
    glViewport(0, 0, w, h);
}

void mouse_callback(GLFWwindow *window, double xpos, double ypos)
{
    if (primeiro_mouse)
    {
        lastX = xpos;
        lastY = ypos;
        primeiro_mouse = false;
    }

    float xoffset = xpos - lastX;
    float yoffset = lastY - ypos;
    lastX = xpos;
    lastY = ypos;

    float sensibilidade = 0.1f;
    xoffset *= sensibilidade;
    yoffset *= sensibilidade;

    Cam_yaw += xoffset;
    Cam_pitch += yoffset;

    if (Cam_pitch > 89.0f)
        Cam_pitch = 89.0f;
    if (Cam_pitch < -89.0f)
        Cam_pitch = -89.0f;
}

void key_callback(GLFWwindow *window, int key, int scancode, int action, int mods)
{
}

// -----------------------------
// Inicialização do OpenGL
// -----------------------------

void inicializaOpenGL()
{
    //Inicializa GLFW
    glfwInit();

    //Criação de uma janela
    Window = glfwCreateWindow(WIDTH, HEIGHT, "Exemplo Base - CG em Tempo Real", nullptr, nullptr);
    glfwMakeContextCurrent(Window);

    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetFramebufferSizeCallback(Window, redimensionaCallback);
    glfwSetKeyCallback(Window, key_callback);
    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);

    cout << "Placa de vídeo: " << glGetString(GL_RENDERER) << endl;
    cout << "Versão do OpenGL: " << glGetString(GL_VERSION) << endl;
}

// -----------------------------
// Inicialização da geometria
// -----------------------------
// Aqui criamos o MODELO geométrico do cubo.
// O cubo é definido uma única vez e pode ser instanciado várias vezes na cena.
//
// Cada vértice carrega dois atributos:
//   - posição (x, y, z)   — location 0
//   - normal  (nx, ny, nz) — location 1
//
// As normais são necessárias para o cálculo de iluminação:
// indicam para qual lado cada face está "olhando", o que determina
// como a luz incide e é espalhada pela superfície.

void inicializaCubo()
{

    // Formato por vértice: [x, y, z,  nx, ny, nz]
    // A normal de cada face é constante - efeito "facetado" (flat shading por face)
    float points[] = {
        // face frontal (+Z) — normal (0, 0, 1)
        0.5, 0.5, 0.5,          0, 0, 1,
        0.5, -0.5, 0.5,         0, 0, 1,
        -0.5, -0.5, 0.5,        0, 0, 1,
        0.5, 0.5, 0.5,          0, 0, 1,
        -0.5, -0.5, 0.5,        0, 0, 1,
        -0.5, 0.5, 0.5,         0, 0, 1,

        // face traseira (-Z) - normal (0, 0, -1)
        0.5, 0.5, -0.5,         0, 0, -1,
        0.5, -0.5, -0.5,        0, 0, -1,
        -0.5, -0.5, -0.5,       0, 0, -1,
        0.5, 0.5, -0.5,         0, 0, -1,
        -0.5, -0.5, -0.5,       0, 0, -1,
        -0.5, 0.5, -0.5,        0, 0, -1,

        // face esquerda (-X) - normal (-1, 0, 0)
        -0.5, -0.5, 0.5,        -1, 0, 0,
        -0.5, 0.5, 0.5,         -1, 0, 0,
        -0.5, -0.5, -0.5,       -1, 0, 0,
        -0.5, -0.5, -0.5,       -1, 0, 0,
        -0.5, 0.5, -0.5,        -1, 0, 0,
        -0.5, 0.5, 0.5,         -1, 0, 0,

        // face direita (+X) - normal (1, 0, 0)
        0.5, -0.5, 0.5,         1, 0, 0,
        0.5, 0.5, 0.5,          1, 0, 0,
        0.5, -0.5, -0.5,        1, 0, 0,
        0.5, -0.5, -0.5,        1, 0, 0,
        0.5, 0.5, -0.5,         1, 0, 0,
        0.5, 0.5, 0.5,          1, 0, 0,

        // face inferior (-Y) - normal (0, -1, 0)
        -0.5, -0.5, 0.5,        0, -1, 0,
        0.5, -0.5, 0.5,         0, -1, 0,
        0.5, -0.5, -0.5,        0, -1, 0,
        0.5, -0.5, -0.5,        0, -1, 0,
        -0.5, -0.5, -0.5,       0, -1, 0,
        -0.5, -0.5, 0.5,        0, -1, 0,

        // face superior (+Y) - normal (0, 1, 0)
        -0.5, 0.5, 0.5,         0, 1, 0,
        0.5, 0.5, 0.5,          0, 1, 0,
        0.5, 0.5, -0.5,         0, 1, 0,
        0.5, 0.5, -0.5,         0, 1, 0,
        -0.5, 0.5, -0.5,        0, 1, 0,
        -0.5, 0.5, 0.5,         0, 1, 0};
    GLuint VBO;
    glGenVertexArrays(1, &Vao_cubo);
    glGenBuffers(1, &VBO);

    glBindVertexArray(Vao_cubo);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(points), points, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void *)0);
    glEnableVertexAttribArray(0);

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void *)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);
}

void inicializaEsfera()
{
    std::vector<float> points;
    
    // Resolução da esfera (quanto maior, mais redonda, porém mais pesada)
    int stacks = 30;  // Fatias horizontais (latitude)
    int sectors = 30; // Fatias verticais (longitude)
    float radius = 0.5f;
    const float PI = 3.14159265359f;

    for (int i = 0; i < stacks; ++i)
    {
        float phi1 = PI * float(i) / stacks;
        float phi2 = PI * float(i + 1) / stacks;

        for (int j = 0; j < sectors; ++j)
        {
            float theta1 = 2.0f * PI * float(j) / sectors;
            float theta2 = 2.0f * PI * float(j + 1) / sectors;

            // Função auxiliar (lambda) para calcular e adicionar um vértice e sua normal
            auto addVertex = [&](float p, float t) {
                // Coordenadas esféricas para cartesianas
                float x = radius * sin(p) * cos(t);
                float y = radius * cos(p);
                float z = radius * sin(p) * sin(t);

                // 1. Adiciona a Posição
                points.push_back(x);
                points.push_back(y);
                points.push_back(z);

                // 2. Adiciona a Normal
                // Para uma esfera centrada na origem (0,0,0), a direção da normal 
                // é exatamente a posição do vértice dividida pelo raio (normalizada).
                points.push_back(x / radius);
                points.push_back(y / radius);
                points.push_back(z / radius);
            };

            // Um "quadrado" na superfície da esfera é formado por 2 triângulos.
            // Triângulo 1
            addVertex(phi1, theta1);
            addVertex(phi2, theta1);
            addVertex(phi1, theta2);

            // Triângulo 2
            addVertex(phi1, theta2);
            addVertex(phi2, theta1);
            addVertex(phi2, theta2);
        }
    }

    // Calcula quantos vértices reais foram gerados (cada vértice tem 6 floats: 3 pos + 3 norm)
    Num_vertices_esfera = points.size() / 6;

    // A partir daqui, é a mesma lógica do seu cubo
    GLuint VBO;
    glGenVertexArrays(1, &Vao_esfera);
    glGenBuffers(1, &VBO);

    glBindVertexArray(Vao_esfera);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    
    // Nota: Usamos points.data() para pegar o ponteiro do vector e points.size() para o tamanho
    glBufferData(GL_ARRAY_BUFFER, points.size() * sizeof(float), points.data(), GL_STATIC_DRAW);

    // Atributo 0: Posição
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void *)0);
    glEnableVertexAttribArray(0);

    // Atributo 1: Normal
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void *)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);
}

// -----------------------------
// Shaders
// -----------------------------
// O vertex shader transforma a posição do vértice e propaga a normal
// para o espaço do mundo, onde a iluminação será calculada.
//
// O fragment shader implementa o modelo de iluminação de Phong:
//   - Ambiente:  Ka × lightColor
//   - Difuso:    Kd × max(dot(N, L), 0) × lightColor
//   - Especular: Ks × max(dot(N, H), 0)^shininess × lightColor
//
// onde:
//   N = normal do fragmento (normalizada)
//   L = direção da luz      (do fragmento para a luz)
//   V = direção da câmera   (do fragmento para a câmera)
//   H = half-vector         (bissetriz entre L e V - modelo de Blinn-Phong)

GLuint compilaShader(const char *source, GLenum type)
{
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);
    return shader;
}

void inicializaShaders()
{
    const char *vertex_shader = R"(
        #version 400
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
    )";

    const char *fragment_shader = R"(
        #version 450

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

        void main()
        {
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
    )";

    GLuint vs = compilaShader(vertex_shader, GL_VERTEX_SHADER);
    GLuint fs = compilaShader(fragment_shader, GL_FRAGMENT_SHADER);

    Shader_programm = glCreateProgram();
    glAttachShader(Shader_programm, vs);
    glAttachShader(Shader_programm, fs);
    glLinkProgram(Shader_programm);

    glDeleteShader(vs);
    glDeleteShader(fs);
}

// -----------------------------
// Transformação de modelo
// -----------------------------
// Define a INSTÂNCIA do modelo no mundo:
// onde ele está, em que escala e com qual rotação.

void transformacaoGenerica(float Tx, float Ty, float Tz,
                           float Sx, float Sy, float Sz,
                           float Rx, float Ry, float Rz)
{
    glm::mat4 transform(1.0f);

    transform = glm::translate(transform, glm::vec3(Tx, Ty, Tz));
    transform = glm::rotate(transform, glm::radians(Rz), glm::vec3(0, 0, 1));
    transform = glm::rotate(transform, glm::radians(Ry), glm::vec3(0, 1, 0));
    transform = glm::rotate(transform, glm::radians(Rx), glm::vec3(1, 0, 0));
    transform = glm::scale(transform, glm::vec3(Sx, Sy, Sz));

    GLuint loc = glGetUniformLocation(Shader_programm, "transform");
    glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(transform));
}

// -----------------------------
// Câmera (matriz de visualização)
// -----------------------------

void especificaMatrizVisualizacao()
{
    /*
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
    */
    glm::vec3 front;
    front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front.y = sin(glm::radians(Cam_pitch));
    front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front = glm::normalize(front);

    glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + front, glm::vec3(0, 1, 0));

    GLuint loc = glGetUniformLocation(Shader_programm, "view");
    glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(view));
}

// -----------------------------
// Projeção
// -----------------------------

void especificaMatrizProjecao()
{
    glm::mat4 proj = glm::perspective(glm::radians(67.0f),
                                      (float)WIDTH / HEIGHT,
                                      0.1f, 100.0f);

    GLuint loc = glGetUniformLocation(Shader_programm, "proj");
    glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(proj));
}

void inicializaCamera()
{
    especificaMatrizVisualizacao();
    especificaMatrizProjecao();
}

// -----------------------------
// Definição de material
// -----------------------------

void defineMaterial(float r, float g, float b,
                    float ka, float kd, float ks,
                    float shininess)
{
    /*
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
    
    */
    glUniform3f(glGetUniformLocation(Shader_programm, "objectColor"),r, g, b);
    glUniform1f(glGetUniformLocation(Shader_programm, "Ka"), ka);
    glUniform1f(glGetUniformLocation(Shader_programm, "Kd"), kd);
    glUniform1f(glGetUniformLocation(Shader_programm, "Ks"), ks);
    glUniform1f(glGetUniformLocation(Shader_programm, "shininess"), shininess);
}

// -----------------------------
// Entrada de teclado
// -----------------------------

void trataTeclado()
{
    /*
    Movimenta a câmera no espaço 3D conforme as teclas WASD.
    A direção do movimento segue o vetor 'frente' (para onde o jogador está
    olhando), incluindo a inclinação vertical (pitch).
    */
    float velocidade = Cam_speed * Tempo_entre_frames;

    glm::vec3 frente;
    frente.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente.y = sin(glm::radians(Cam_pitch));
    frente.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente = glm::normalize(frente);

    glm::vec3 direita = glm::normalize(glm::cross(frente, glm::vec3(0, 1, 0)));

    if (glfwGetKey(Window, GLFW_KEY_W) == GLFW_PRESS)
        Cam_pos += frente * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_S) == GLFW_PRESS)
        Cam_pos -= frente * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_A) == GLFW_PRESS)
        Cam_pos -= direita * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_D) == GLFW_PRESS)
        Cam_pos += direita * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        glfwSetWindowShouldClose(Window, true);
}

// -----------------------------
// Loop de renderização
// -----------------------------
void inicializaRenderizacao()
{
    float tempo_anterior = glfwGetTime();

    // Ativa o teste de profundidade para que faces mais próximas sobreponham as mais distantes
    glEnable(GL_DEPTH_TEST);

    // Luz posicionada fixa no espaço do mundo
    glm::vec3 lightPos(2.0f, 2.0f, 2.0f);

    while (!glfwWindowShouldClose(Window))
    {
        //Calcula quantos segundos se passaram entre um frame e outro
        float tempo_atual = glfwGetTime();
        Tempo_entre_frames = tempo_atual - tempo_anterior;
        tempo_anterior = tempo_atual;

        glClearColor(0.2f, 0.3f, 0.3f, 1.0f); // define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT); // limpa os buffers de cor e profundidade

        glUseProgram(Shader_programm);
        inicializaCamera();

        glBindVertexArray(Vao_cubo);

        // Envia a posição da luz e da câmera para o shader (necessárias para Phong)
        glUniform3fv(glGetUniformLocation(Shader_programm, "lightPos"), 1, glm::value_ptr(lightPos));
        glUniform3fv(glGetUniformLocation(Shader_programm, "viewPos"), 1, glm::value_ptr(Cam_pos));

        // Luz branca pura
        glUniform3f(glGetUniformLocation(Shader_programm, "lightColor"), 1.0f, 1.0f, 1.0f);

        // Configuração da Atenuação ---
        // Estes valores representam uma luz que cobre uma distância de cerca de 50 unidades.
        // Você pode ajustá-los para fazer a luz ir mais ou menos longe.
        glUniform1f(glGetUniformLocation(Shader_programm, "Kc"), 1.0f);   // Constante
        glUniform1f(glGetUniformLocation(Shader_programm, "Kl"), 0.09f);  // Linear
        glUniform1f(glGetUniformLocation(Shader_programm, "Kq"), 0.032f); // Quadrática
                    
        defineMaterial(
            1.0f, 0.6f, 0.2f,   // cor base
            0.1f,               // Ka
            0.7f,               // Kd
            1.0f,               // Ks
            32.0f               // shininess
        );
        //transformacaoGenerica(0, 0, 0, 1, 1, 1, 0, 0, 0);
        //glDrawArrays(GL_TRIANGLES, 0, 36);

        // 2. Desenha a Esfera
        glBindVertexArray(Vao_esfera);
        transformacaoGenerica(0, 0, 0, 1, 1, 1, 0, 0, 0);
        glDrawArrays(GL_TRIANGLES, 0, Num_vertices_esfera); // <-- Usa a variável dinâmica que criamos

        glfwSwapBuffers(Window);
        glfwPollEvents();
        trataTeclado();
    }

    glfwTerminate();
}

// -----------------------------
// Função principal
// -----------------------------

int main()
{
    inicializaOpenGL();
    inicializaCubo();
    inicializaEsfera();
    inicializaShaders();
    inicializaRenderizacao();
    return 0;
}