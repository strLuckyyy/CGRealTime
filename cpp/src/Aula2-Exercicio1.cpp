// Câmera e exemplo base para a disciplina de Computação Gráfica em Tempo Real
//
// Este código serve como base para toda a disciplina.
// Ele implementa:
// - OpenGL moderno (pipeline programável)
// - Um modelo geométrico simples (cubo)
// - Transformações de modelo, visualização (câmera) e projeção
// - Uma câmera no estilo FPS (yaw + pitch)
//
// A partir deste exemplo, novos conceitos serão adicionados gradualmente
// (iluminação, materiais, texturas, visibilidade, sombras, etc.)

/*
    Exercicio:
        1. A partir do código base, desenhe dois cubos na cena usando o mesmo VAO, cada um em uma posição diferente do espaço.

        2. Atribua cores diferentes para cada cubo usando o uniform corobjeto.

        3. Faça com que um dos cubos gire continuamente em torno de um eixo à sua escolha, usando o tempo entre frames (Tempo_entre_frames) para controlar a rotação.

        4. Faça com que o outro cubo permaneça parado, servindo como referência visual para a rotação do primeiro.

        5. Implemente um terceiro cubo, também reutilizando o mesmo VAO, posicionado em outro ponto da cena.

        6. Faça com que esse terceiro cubo se mova continuamente para frente e para trás ao longo de um eixo (ex.: eixo Z), usando o tempo entre frames para controlar a velocidade.

        7. Associe uma tecla do teclado para aumentar e diminuir a escala de todos os cubos simultaneamente.

        8. Associe outra tecla para ativar ou desativar a rotação do cubo que gira.

        9. Modifique o código para que todos os cubos sejam desenhados dentro de um único loop, usando uma estrutura de dados simples (por exemplo, uma lista de posições).

        10. Organize o código de forma que fique claro:
            - onde o modelo geométrico é definido
            - onde as instâncias (cubos) são posicionadas
            - onde ocorre a renderização de cada instância
*/

#include <iostream>
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

using namespace std;

// Cube Database
struct Cube
{
    glm::vec3 position;
    glm::vec4 color;
    glm::vec3 rotation;
    bool rotAnimacao = false;
    bool transAnimacao = false;
    float tz = 0.f;
    int sentido = 1;
};

Cube cubes[] = {
    Cube{
        .position = glm::vec3(0.f, 0.f, 0.f),
        .color = glm::vec4(1.f, 0.f, 0.f, 1.f),
        .rotation = glm::vec3(0.f, 0.f, 0.f)
    },
    Cube{
        .position = glm::vec3(1.f, 1.f, 1.f),
        .color = glm::vec4(0.f, 1.f, 1.f, 1.f),
        .rotation = glm::vec3(0.f, 0.f, 0.f),
        .rotAnimacao = true
    },
    Cube{
        .position = glm::vec3(2.f, -1.f, 0.f),
        .color = glm::vec4(0.f, 0.f, 1.f, 1.f),
        .rotation = glm::vec3(0.f, 0.f, 0.f),
        .transAnimacao = true
    }
};
// End of Cube Database

GLFWwindow* Window = nullptr;
GLuint Shader_programm = 0;
GLuint Vao_cubo = 0;

int WIDTH = 800;
int HEIGHT = 600;

float Tempo_entre_frames = 0.0f;

float Size = 1.f;
bool CanRotate = true;
int rotation = 0;

// -----------------------------
// Parâmetros da câmera virtual
// -----------------------------

float Cam_speed = 10.0f;        
float Cam_yaw_speed = 30.0f;    
glm::vec3 Cam_pos(0.0f, 0.0f, 2.0f);
float Cam_yaw = 0.0f;
float Cam_pitch = 0.0f;

double lastX = WIDTH / 2.0;
double lastY = HEIGHT / 2.0;
bool primeiro_mouse = true;

// -----------------------------
// Callbacks de janela e entrada
// -----------------------------

void redimensionaCallback(GLFWwindow* window, int w, int h)
{
    WIDTH = w;
    HEIGHT = h;
    glViewport(0, 0, w, h);
}

void mouse_callback(GLFWwindow* window, double xpos, double ypos)
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

    if (Cam_pitch > 89.0f) Cam_pitch = 89.0f;
    if (Cam_pitch < -89.0f) Cam_pitch = -89.0f;
}

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mods)
{
}

// -----------------------------
// Inicialização do OpenGL
// -----------------------------

void inicializaOpenGL()
{
    glfwInit();

    Window = glfwCreateWindow(WIDTH, HEIGHT, "Exemplo Base - CG em Tempo Real", nullptr, nullptr);
    glfwMakeContextCurrent(Window);

    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);

    glfwSetFramebufferSizeCallback(Window, redimensionaCallback);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetKeyCallback(Window, key_callback);
    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);

    cout << "Placa de vídeo: " << glGetString(GL_RENDERER) << endl;
    cout << "Versão do OpenGL: " << glGetString(GL_VERSION) << endl;
}

// -----------------------------
// Inicialização da geometria
// -----------------------------

void inicializaCubo()
{
    float points[] = {
        0.5,0.5,0.5, 0.5,-0.5,0.5, -0.5,-0.5,0.5,
        0.5,0.5,0.5, -0.5,-0.5,0.5, -0.5,0.5,0.5,

        0.5,0.5,-0.5, 0.5,-0.5,-0.5, -0.5,-0.5,-0.5,
        0.5,0.5,-0.5, -0.5,-0.5,-0.5, -0.5,0.5,-0.5,

        -0.5,-0.5,0.5, -0.5,0.5,0.5, -0.5,-0.5,-0.5,
        -0.5,-0.5,-0.5, -0.5,0.5,-0.5, -0.5,0.5,0.5,

        0.5,-0.5,0.5, 0.5,0.5,0.5, 0.5,-0.5,-0.5,
        0.5,-0.5,-0.5, 0.5,0.5,-0.5, 0.5,0.5,0.5,

        -0.5,-0.5,0.5, 0.5,-0.5,0.5, 0.5,-0.5,-0.5,
        0.5,-0.5,-0.5, -0.5,-0.5,-0.5, -0.5,-0.5,0.5,

        -0.5,0.5,0.5, 0.5,0.5,0.5, 0.5,0.5,-0.5,
        0.5,0.5,-0.5, -0.5,0.5,-0.5, -0.5,0.5,0.5
    };

    GLuint VBO;
    glGenVertexArrays(1, &Vao_cubo);
    glGenBuffers(1, &VBO);

    glBindVertexArray(Vao_cubo);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(points), points, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, (void*)0);
    glEnableVertexAttribArray(0);
}

// -----------------------------
// Shaders
// -----------------------------

GLuint compilaShader(const char* source, GLenum type)
{
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);
    return shader;
}

void inicializaShaders()
{
    const char* vertex_shader = R"(
        #version 450
        layout(location = 0) in vec3 vertex_posicao;

        uniform mat4 transform;
        uniform mat4 view;
        uniform mat4 proj;

        void main() {
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
        }
    )";

    const char* fragment_shader = R"(
        #version 450
        out vec4 frag_colour;
        uniform vec4 corobjeto;

        void main() {
            frag_colour = corobjeto;
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

void transformacaoGenerica(float Tx,float Ty,float Tz,
                           float Sx,float Sy,float Sz,
                           float Rx,float Ry,float Rz)
{
    glm::mat4 transform(1.0f);

    transform = glm::translate(transform, glm::vec3(Tx,Ty,Tz));
    transform = glm::rotate(transform, glm::radians(Rz), glm::vec3(0,0,1));
    transform = glm::rotate(transform, glm::radians(Ry), glm::vec3(0,1,0));
    transform = glm::rotate(transform, glm::radians(Rx), glm::vec3(1,0,0));
    transform = glm::scale(transform, glm::vec3(Sx,Sy,Sz));

    GLuint loc = glGetUniformLocation(Shader_programm, "transform");
    glUniformMatrix4fv(loc,1,GL_FALSE,glm::value_ptr(transform));
}

// -----------------------------
// Câmera (matriz de visualização)
// -----------------------------

void especificaMatrizVisualizacao()
{
    glm::vec3 front;
    front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front.y = sin(glm::radians(Cam_pitch));
    front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front = glm::normalize(front);

    glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + front, glm::vec3(0,1,0));

    GLuint loc = glGetUniformLocation(Shader_programm, "view");
    glUniformMatrix4fv(loc,1,GL_FALSE,glm::value_ptr(view));
}

// -----------------------------
// Projeção
// -----------------------------

void especificaMatrizProjecao()
{
    glm::mat4 proj = glm::perspective(glm::radians(67.0f),
                                      (float)WIDTH/HEIGHT,
                                      0.1f,100.0f);

    GLuint loc = glGetUniformLocation(Shader_programm, "proj");
    glUniformMatrix4fv(loc,1,GL_FALSE,glm::value_ptr(proj));
}

void inicializaCamera()
{
    especificaMatrizVisualizacao();
    especificaMatrizProjecao();
}

// -----------------------------
// Entrada de teclado
// -----------------------------

void trataTeclado()
{
    float velocidade = Cam_speed * Tempo_entre_frames;

    glm::vec3 frente;
    frente.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente.y = sin(glm::radians(Cam_pitch));
    frente.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente = glm::normalize(frente);

    glm::vec3 direita = glm::normalize(glm::cross(frente, glm::vec3(0,1,0)));

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
    
    // Size
    if (glfwGetKey(Window, GLFW_KEY_UP) == GLFW_PRESS)
        Size += 1.f * Tempo_entre_frames;
    if (glfwGetKey(Window, GLFW_KEY_DOWN) == GLFW_PRESS)
        Size -= 1.f * Tempo_entre_frames;

    if (Size < 0.1f) Size = 0.1f;
    if (Size > 3.f) Size = 3.f;
    // End Size

    // Rotation
    if (glfwGetKey(Window, GLFW_KEY_1) == GLFW_PRESS)
        CanRotate = false;
    if (glfwGetKey(Window, GLFW_KEY_2) == GLFW_PRESS)
        CanRotate = true;
    // End Rotation
}

// -----------------------------
// Renderização
// -----------------------------

void defineCor(float r,float g,float b,float a)
{
    GLuint loc = glGetUniformLocation(Shader_programm, "corobjeto");
    glUniform4f(loc,r,g,b,a);
}

void inicializaRenderizacao()
{
    float tempo_anterior = glfwGetTime();

    glEnable(GL_DEPTH_TEST);

    int trans = 5;
    int distancia = 3;

    while(!glfwWindowShouldClose(Window))
    {
        float tempo_atual = glfwGetTime();
        Tempo_entre_frames = tempo_atual - tempo_anterior;
        tempo_anterior = tempo_atual;

        glClearColor(0.2f,0.3f,0.3f,1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glUseProgram(Shader_programm);
        inicializaCamera();

        glBindVertexArray(Vao_cubo);

        for(Cube& cube : cubes)
        {
            // CUBO RODANDO
            if(cube.rotAnimacao && CanRotate)
            {
                cube.rotation[0] += 80.f * Tempo_entre_frames;
                if(cube.rotation[0] > 360.f) cube.rotation[0] = 0.f;
            }

            // CUBO TRANSITANDO
            if(cube.transAnimacao)
            {
                if(cube.tz > distancia) cube.sentido = -1;
                if(cube.tz < -distancia) cube.sentido = 1;

                cube.tz += cube.sentido * trans * Tempo_entre_frames;
            }
        
            defineCor(cube.color[0], cube.color[1], cube.color[2], cube.color[3]);

            transformacaoGenerica(
                cube.position[0], cube.position[1], cube.position[2] + cube.tz,
                Size, Size, Size,
                cube.rotation[0], cube.rotation[1], cube.rotation[2]
            );

            glDrawArrays(GL_TRIANGLES,0,36);
        }

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
    inicializaShaders();
    inicializaRenderizacao();
    return 0;
}