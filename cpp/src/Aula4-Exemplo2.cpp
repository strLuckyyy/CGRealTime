// Batching e Draw Calls - exemplo para a disciplina de Computação Gráfica em Tempo Real
//
// Este exemplo demonstra o impacto de múltiplas draw calls versus batching no desempenho.
//
// Conceitos demonstrados:
// - Draw call: cada chamada glDrawArrays/glDrawElements tem custo de CPU
// - Sem batching: N cubos = N draw calls (gargalo de CPU mesmo com poucos triângulos)
// - Com batching: N cubos = 1 draw call (geometria consolidada em um único VAO)
//
// Controles:
//   W/A/S/D     - mover câmera (FPS)
//   Mouse       - girar câmera
//   B           - alternar entre modo SEM batching e COM batching
//   +/-         - aumentar/diminuir número de cubos na cena
//   ESC         - fechar
//
// HUD no terminal (a cada ~1 segundo):
//   Modo atual, número de cubos, draw calls por frame, FPS médio

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

using namespace std;

// Estrutura para armazenar transformações simples
struct Transform {
    float tx, ty, tz, sx, sy, sz;
};

GLFWwindow* Window = nullptr;
GLuint Shader_programm = 0;

int WIDTH = 800;
int HEIGHT = 600;

float Tempo_entre_frames = 0.0f;

// -----------------------------
// Parâmetros da câmera virtual
// -----------------------------

float Cam_speed = 10.0f;
float Cam_yaw_speed = 30.0f;
glm::vec3 Cam_pos(0.0f, 2.0f, 12.0f);
float Cam_yaw = 180.0f; // olhando para a cena
float Cam_pitch = -10.0f;

double lastX = WIDTH / 2.0;
double lastY = HEIGHT / 2.0;
bool primeiro_mouse = true;

// -----------------------------
// Estado da demonstração
// -----------------------------

bool Modo_batching = false;
int Num_cubos = 500;

GLuint Vao_cubo_unitario = 0;
GLuint Vao_batch = 0;
GLuint Vbo_batch = 0;
int Batch_vertex_count = 0;

vector<Transform> Cubos_transforms;

// Acumuladores de FPS para o HUD
float _fps_acumulado = 0;
int _fps_frames = 0;
double _fps_timer = 0.0;

// Protótipos das funções de gerenciamento de geometria
void _recria_cubos();

// -----------------------------
// Callbacks de janela e entrada
// -----------------------------

void redimensionaCallback(GLFWwindow* window, int w, int h) {
    WIDTH = w;
    HEIGHT = h;
    glViewport(0, 0, w, h);
}

void mouse_callback(GLFWwindow* window, double xpos, double ypos) {
    if (primeiro_mouse) {
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

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mods) {
    if (action != GLFW_PRESS) return;

    if (key == GLFW_KEY_B) {
        Modo_batching = !Modo_batching;
        string modo_str = Modo_batching ? "COM batching (1 draw call)" : "SEM batching (N draw calls)";
        cout << "\n[MODO] " << modo_str << endl;
    }

    if (key == GLFW_KEY_EQUAL || key == GLFW_KEY_KP_ADD) {
        Num_cubos = min(Num_cubos + 100, 5000);
        _recria_cubos();
        cout << "[CUBOS] " << Num_cubos << " cubos na cena" << endl;
    }

    if (key == GLFW_KEY_MINUS || key == GLFW_KEY_KP_SUBTRACT) {
        Num_cubos = max(Num_cubos - 100, 100);
        _recria_cubos();
        cout << "[CUBOS] " << Num_cubos << " cubos na cena" << endl;
    }
}

// -----------------------------
// Inicialização do OpenGL
// -----------------------------

void inicializaOpenGL() {
    glfwInit();
    Window = glfwCreateWindow(WIDTH, HEIGHT, "Exemplo Batching - CG em Tempo Real", nullptr, nullptr);
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
// Geometria: vértices de 1 cubo
// -----------------------------

vector<float> _vertices_cubo() {
    return {
         0.5, 0.5, 0.5,  0.5,-0.5, 0.5, -0.5,-0.5, 0.5,
         0.5, 0.5, 0.5, -0.5,-0.5, 0.5, -0.5, 0.5, 0.5,
         0.5, 0.5,-0.5,  0.5,-0.5,-0.5, -0.5,-0.5,-0.5,
         0.5, 0.5,-0.5, -0.5,-0.5,-0.5, -0.5, 0.5,-0.5,
        -0.5,-0.5, 0.5, -0.5, 0.5, 0.5, -0.5,-0.5,-0.5,
        -0.5,-0.5,-0.5, -0.5, 0.5,-0.5, -0.5, 0.5, 0.5,
         0.5,-0.5, 0.5,  0.5, 0.5, 0.5,  0.5,-0.5,-0.5,
         0.5,-0.5,-0.5,  0.5, 0.5,-0.5,  0.5, 0.5, 0.5,
        -0.5,-0.5, 0.5,  0.5,-0.5, 0.5,  0.5,-0.5,-0.5,
         0.5,-0.5,-0.5, -0.5,-0.5,-0.5, -0.5,-0.5, 0.5,
        -0.5, 0.5, 0.5,  0.5, 0.5, 0.5,  0.5, 0.5,-0.5,
         0.5, 0.5,-0.5, -0.5, 0.5,-0.5, -0.5, 0.5, 0.5
    };
}

void inicializaCuboUnitario() {
    vector<float> points = _vertices_cubo();
    GLuint VBO;
    glGenVertexArrays(1, &Vao_cubo_unitario);
    glGenBuffers(1, &VBO);

    glBindVertexArray(Vao_cubo_unitario);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, points.size() * sizeof(float), points.data(), GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, (void*)0);
    glEnableVertexAttribArray(0);
}

// -----------------------------
// Geração dos transforms
// -----------------------------

vector<Transform> _gera_transforms(int n) {
    int lado = (int)ceil(sqrt(n));
    vector<Transform> result;
    srand(42); // Seed fixa

    for (int i = 0; i < n; ++i) {
        int col = i % lado;
        int row = i / lado;
        float tx = (col - lado / 2.0f) * 2.2f;
        float ty = 0.0f;
        float tz = (row - lado / 2.0f) * 2.2f;
        float s = 0.4f + static_cast <float> (rand()) / (static_cast <float> (RAND_MAX / (0.9f - 0.4f)));
        result.push_back({tx, ty, tz, s, s, s});
    }
    return result;
}

// -----------------------------
// Construção do batch
// -----------------------------

void _constroi_batch(const vector<Transform>& transforms) {
    vector<float> cubo_base = _vertices_cubo();
    vector<float> merged;
    merged.reserve(transforms.size() * cubo_base.size());

    for (const auto& t : transforms) {
        for (size_t i = 0; i < cubo_base.size(); i += 3) {
            merged.push_back(cubo_base[i] * t.sx + t.tx);
            merged.push_back(cubo_base[i + 1] * t.sy + t.ty);
            merged.push_back(cubo_base[i + 2] * t.sz + t.tz);
        }
    }

    if (Vao_batch == 0) glGenVertexArrays(1, &Vao_batch);
    if (Vbo_batch == 0) glGenBuffers(1, &Vbo_batch);

    glBindVertexArray(Vao_batch);
    glBindBuffer(GL_ARRAY_BUFFER, Vbo_batch);
    glBufferData(GL_ARRAY_BUFFER, merged.size() * sizeof(float), merged.data(), GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, (void*)0);
    glEnableVertexAttribArray(0);

    Batch_vertex_count = (int)(merged.size() / 3);
}

void _recria_cubos() {
    Cubos_transforms = _gera_transforms(Num_cubos);
    _constroi_batch(Cubos_transforms);
}

// -----------------------------
// Shaders
// -----------------------------

GLuint compilaShader(const char* source, GLenum type) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);
    return shader;
}

void inicializaShaders() {
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
// Transformações
// -----------------------------

void transformacaoGenerica(float Tx, float Ty, float Tz, float Sx, float Sy, float Sz) {
    glm::mat4 transform(1.0f);
    transform = glm::translate(transform, glm::vec3(Tx, Ty, Tz));
    transform = glm::scale(transform, glm::vec3(Sx, Sy, Sz));

    GLuint loc = glGetUniformLocation(Shader_programm, "transform");
    glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(transform));
}

void transformacaoIdentidade() {
    glm::mat4 id(1.0f);
    GLuint loc = glGetUniformLocation(Shader_programm, "transform");
    glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(id));
}

// -----------------------------
// Câmera e Projeção
// -----------------------------

void especificaMatrizVisualizacao() {
    glm::vec3 front;
    front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front.y = sin(glm::radians(Cam_pitch));
    front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front = glm::normalize(front);

    glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + front, glm::vec3(0, 1, 0));
    GLuint loc = glGetUniformLocation(Shader_programm, "view");
    glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(view));
}

void especificaMatrizProjecao() {
    glm::mat4 proj = glm::perspective(glm::radians(67.0f), (float)WIDTH / HEIGHT, 0.1f, 200.0f);
    GLuint loc = glGetUniformLocation(Shader_programm, "proj");
    glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(proj));
}

void inicializaCamera() {
    especificaMatrizVisualizacao();
    especificaMatrizProjecao();
}

// -----------------------------
// Entrada e HUD
// -----------------------------

void trataTeclado() {
    float velocidade = Cam_speed * Tempo_entre_frames;
    glm::vec3 frente;
    frente.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente.y = sin(glm::radians(Cam_pitch));
    frente.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente = glm::normalize(frente);
    glm::vec3 direita = glm::normalize(glm::cross(frente, glm::vec3(0, 1, 0)));

    if (glfwGetKey(Window, GLFW_KEY_W) == GLFW_PRESS) Cam_pos += frente * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_S) == GLFW_PRESS) Cam_pos -= frente * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_A) == GLFW_PRESS) Cam_pos -= direita * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_D) == GLFW_PRESS) Cam_pos += direita * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_ESCAPE) == GLFW_PRESS) glfwSetWindowShouldClose(Window, true);
}

void defineCor(float r, float g, float b, float a) {
    GLuint loc = glGetUniformLocation(Shader_programm, "corobjeto");
    glUniform4f(loc, r, g, b, a);
}

void atualizaHUD(int draw_calls, float fps) {
    string modo_str = Modo_batching ? "COM batching (1 draw call)" : "SEM batching (N draw calls)";
    int triangulos = Num_cubos * 12;
    printf("\r[%s]  Cubos: %4d  |  Triângulos: %6d  |  Draw calls: %4d  |  FPS: %6.1f   ",
           modo_str.c_str(), Num_cubos, triangulos, draw_calls, fps);
    fflush(stdout);
}

// -----------------------------
// Renderização
// -----------------------------

int renderizaSemBatching() {
    glBindVertexArray(Vao_cubo_unitario);
    defineCor(0.3f, 0.6f, 1.0f, 1.0f);
    for (const auto& t : Cubos_transforms) {
        transformacaoGenerica(t.tx, t.ty, t.tz, t.sx, t.sy, t.sz);
        glDrawArrays(GL_TRIANGLES, 0, 36);
    }
    return (int)Cubos_transforms.size();
}

int renderizaComBatching() {
    glBindVertexArray(Vao_batch);
    defineCor(1.0f, 0.6f, 0.2f, 1.0f);
    transformacaoIdentidade();
    glDrawArrays(GL_TRIANGLES, 0, Batch_vertex_count);
    return 1;
}

void inicializaRenderizacao() {
    float tempo_anterior = (float)glfwGetTime();
    _fps_timer = tempo_anterior;

    glEnable(GL_DEPTH_TEST);

    cout << "\n--- Exemplo: Draw Calls e Batching ---" << endl;
    cout << "  B      - alternar modo (sem / com batching)" << endl;
    cout << "  +/-    - mais/menos cubos na cena" << endl;
    cout << "  W/A/S/D + mouse - câmera FPS" << endl;
    cout << "  ESC    - fechar\n" << endl;

    while (!glfwWindowShouldClose(Window)) {
        float tempo_atual = (float)glfwGetTime();
        Tempo_entre_frames = tempo_atual - tempo_anterior;
        tempo_anterior = tempo_atual;

        glClearColor(0.15f, 0.15f, 0.2f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glUseProgram(Shader_programm);
        inicializaCamera();

        int draw_calls = Modo_batching ? renderizaComBatching() : renderizaSemBatching();

        glfwSwapBuffers(Window);
        glfwPollEvents();
        trataTeclado();

        _fps_frames++;
        _fps_acumulado += (Tempo_entre_frames > 0) ? (1.0f / Tempo_entre_frames) : 0.0f;

        if (tempo_atual - _fps_timer >= 1.0) {
            float fps_medio = _fps_acumulado / _fps_frames;
            atualizaHUD(draw_calls, fps_medio);
            _fps_acumulado = 0; _fps_frames = 0; _fps_timer = tempo_atual;
        }
    }
    glfwTerminate();
}

int main() {
    inicializaOpenGL();
    inicializaShaders();
    inicializaCuboUnitario();
    _recria_cubos();
    inicializaRenderizacao();
    return 0;
}