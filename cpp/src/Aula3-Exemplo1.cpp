/* Malha Interativa — exemplo para a disciplina de Computação Gráfica em Tempo Real
 * * Este exemplo demonstra os conceitos fundamentais de modelagem geométrica:
 * vértices, faces, triângulos e o impacto da resolução da malha na forma do objeto.
 * * Versão C++ adaptada para usar GLAD, GLFW e GLM.
 */

#include <iostream>
#include <string>
#include <vector>
#include <cmath>
#include <iomanip>

// GLAD: Deve ser incluído antes do GLFW
#include <glad/glad.h>
// GLFW
#include <GLFW/glfw3.h>
// GLM
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

using namespace std;

// --- Protótipos das funções ---
void inicializaOpenGL();
void inicializaShaders();
void inicializaCubo();
void inicializaPiramide();
void inicializaEsfera();
void inicializaRenderizacao();
void especificaMatrizVisualizacao();
void especificaMatrizProjecao();
void trataTeclado();
void defineCor(float r, float g, float b, float a);
void transformacaoGenerica(float Tx, float Ty, float Tz, float Sx, float Sy, float Sz, float Rx, float Ry, float Rz);
GLuint montaVAO(const std::vector<float>& dados);
glm::vec3 calculaNormal(glm::vec3 v0, glm::vec3 v1, glm::vec3 v2);
void atualizaHUD(double fps);

// Callbacks
void redimensionaCallback(GLFWwindow* window, int w, int h);
void mouse_callback(GLFWwindow* window, double xpos, double ypos);
void key_callback(GLFWwindow* window, int key, int scancode, int action, int mode);

// --- Variáveis Globais ---
GLFWwindow* Window = nullptr;
GLuint Shader_programm;

// Um VAO por objeto — cada um tem sua própria geometria
GLuint Vao_cubo, Vao_piramide, Vao_esfera;

int WIDTH = 800, HEIGHT = 600;

double Tempo_entre_frames = 0; // variável utilizada para movimentar a câmera

// Variáveis referentes à câmera virtual e sua projeção
float Cam_speed = 8.0f;        // velocidade da câmera, 8 unidades por segundo
glm::vec3 Cam_pos = glm::vec3(0.0f, 0.5f, 7.0f); // posição inicial da câmera
float Cam_yaw = -90.0f;        // Aponta para o fundo da cena (eixo -Z)
float Cam_pitch = -4.0f;       // Inclina levemente para baixo para focar a base
double lastX = 400, lastY = 300;
bool primeiro_mouse = true;

// Estado da demonstração
int Resolucao_esfera = 8;
int Tri_cubo = 0, Tri_piramide = 0, Tri_esfera = 0;
bool Wireframe = false;

// Acumuladores de FPS para o HUD
double _fps_acumulado = 0.0;
int _fps_frames = 0;
double _fps_timer = 0.0;

// -----------------------------
// Shaders (em blocos legíveis)
// -----------------------------

void inicializaShaders() {
    // Vertex Shader: recebe posição E normal
    const GLchar* vertexShaderSource = R"(
        #version 450
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec3 normal;
        
        uniform mat4 transform;
        uniform mat4 view;
        uniform mat4 proj;
        
        out vec3 normal_mundo;

        void main() {
            gl_Position = proj * view * transform * vec4(position, 1.0);
            normal_mundo = mat3(transform) * normal;
        }
    )";

    // Fragment Shader: aplica iluminação direcional simples
    const GLchar* fragmentShaderSource = R"(
        #version 450
        in vec3 normal_mundo;
        out vec4 frag_colour;
        
        uniform vec4 corobjeto;
        uniform vec3 luz_dir;

        void main() {
            vec3 n = normalize(normal_mundo);
            float difuso = max(dot(n, luz_dir), 0.0) * 0.8;
            float ambiente = 0.2;
            float intensidade = difuso + ambiente;
            frag_colour = vec4(corobjeto.rgb * intensidade, corobjeto.a);
        }
    )";

    // Compilação idêntica ao processo do Hello3D.cpp
    GLuint vertexShader = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertexShader, 1, &vertexShaderSource, NULL);
    glCompileShader(vertexShader);

    GLuint fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fragmentShader, 1, &fragmentShaderSource, NULL);
    glCompileShader(fragmentShader);

    Shader_programm = glCreateProgram();
    glAttachShader(Shader_programm, vertexShader);
    glAttachShader(Shader_programm, fragmentShader);
    glLinkProgram(Shader_programm);

    glDeleteShader(vertexShader);
    glDeleteShader(fragmentShader);
}

// -----------------------------
// Funções de Geometria
// -----------------------------

glm::vec3 calculaNormal(glm::vec3 v0, glm::vec3 v1, glm::vec3 v2) {
    // Calcula a normal de face (produto vetorial das arestas)
    glm::vec3 a = v1 - v0;
    glm::vec3 b = v2 - v0;
    glm::vec3 n = glm::cross(a, b);
    if (glm::length(n) < 1e-8) return glm::vec3(0.0f, 1.0f, 0.0f);
    return glm::normalize(n);
}

GLuint montaVAO(const std::vector<float>& dados) {
    GLuint VBO, VAO;
    glGenBuffers(1, &VBO);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, dados.size() * sizeof(float), dados.data(), GL_STATIC_DRAW);

    glGenVertexArrays(1, &VAO);
    glBindVertexArray(VAO);
    
    // Atributo 0: posição (x, y, z) - stride de 6 floats
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    // Atributo 1: normal (nx, ny, nz) - offset de 3 floats
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
    return VAO;
}

// Implementações de inicializaCubo, Piramide e Esfera seguem a lógica do vector
void inicializaCubo() {
    struct Face { std::vector<glm::vec3> v; glm::vec3 n; };
    std::vector<Face> faces = {
        {{{-0.5,-0.5, 0.5},{ 0.5,-0.5, 0.5},{ 0.5, 0.5, 0.5},{-0.5, 0.5, 0.5}}, { 0, 0, 1}},
        {{{ 0.5,-0.5,-0.5},{-0.5,-0.5,-0.5},{-0.5, 0.5,-0.5},{ 0.5, 0.5,-0.5}}, { 0, 0,-1}},
        {{{ 0.5,-0.5, 0.5},{ 0.5,-0.5,-0.5},{ 0.5, 0.5,-0.5},{ 0.5, 0.5, 0.5}}, { 1, 0, 0}},
        {{{-0.5,-0.5,-0.5},{-0.5,-0.5, 0.5},{-0.5, 0.5, 0.5},{-0.5, 0.5,-0.5}}, {-1, 0, 0}},
        {{{-0.5, 0.5, 0.5},{ 0.5, 0.5, 0.5},{ 0.5, 0.5,-0.5},{-0.5, 0.5,-0.5}}, { 0, 1, 0}},
        {{{-0.5,-0.5,-0.5},{ 0.5,-0.5,-0.5},{ 0.5,-0.5, 0.5},{-0.5,-0.5, 0.5}}, { 0,-1, 0}}
    };
    std::vector<float> dados;
    for (auto& f : faces) {
        int idx[] = {0, 1, 2, 0, 2, 3};
        for (int i : idx) {
            dados.push_back(f.v[i].x); dados.push_back(f.v[i].y); dados.push_back(f.v[i].z);
            dados.push_back(f.n.x);    dados.push_back(f.n.y);    dados.push_back(f.n.z);
        }
    }
    Tri_cubo = (int)dados.size() / 18;
    Vao_cubo = montaVAO(dados);
}

void inicializaPiramide() {
    glm::vec3 topo(0.0, 0.8, 0.0), ffd(-0.5, -0.4, 0.5), ffe(0.5, -0.4, 0.5), tfd(-0.5, -0.4, -0.5), tfe(0.5, -0.4, -0.5);
    std::vector<std::vector<glm::vec3>> triangles = { {topo, ffd, ffe}, {topo, ffe, tfe}, {topo, tfe, tfd}, {topo, tfd, ffd}, {ffd, tfd, tfe}, {ffd, tfe, ffe} };
    std::vector<float> dados;
    for (auto& t : triangles) {
        glm::vec3 n = calculaNormal(t[0], t[1], t[2]);
        for (int i = 0; i < 3; i++) {
            dados.push_back(t[i].x); dados.push_back(t[i].y); dados.push_back(t[i].z);
            dados.push_back(n.x);    dados.push_back(n.y);    dados.push_back(n.z);
        }
    }
    Tri_piramide = (int)dados.size() / 18;
    Vao_piramide = montaVAO(dados);
}

void inicializaEsfera() {
    int rings = Resolucao_esfera, sectors = Resolucao_esfera;
    float raio = 0.8f;
    std::vector<float> dados;
    for (int r = 0; r < rings; r++) {
        for (int s = 0; s < sectors; s++) {
            float theta0 = (float)M_PI * r / rings; float theta1 = (float)M_PI * (r + 1) / rings;
            float phi0 = 2.0f * (float)M_PI * s / sectors; float phi1 = 2.0f * (float)M_PI * (s + 1) / sectors;
            auto getV = [&](float t, float p) { return glm::vec3(sin(t)*cos(p), cos(t), sin(t)*sin(p)) * raio; };
            glm::vec3 v00 = getV(theta0, phi0), v01 = getV(theta0, phi1), v10 = getV(theta1, phi0), v11 = getV(theta1, phi1);
            glm::vec3 n1 = calculaNormal(v00, v10, v11);
            glm::vec3 t1[] = {v00, v10, v11};
            for(auto& v : t1){ dados.push_back(v.x); dados.push_back(v.y); dados.push_back(v.z); dados.push_back(n1.x); dados.push_back(n1.y); dados.push_back(n1.z); }
            glm::vec3 n2 = calculaNormal(v00, v11, v01);
            glm::vec3 t2[] = {v00, v11, v01};
            for(auto& v : t2){ dados.push_back(v.x); dados.push_back(v.y); dados.push_back(v.z); dados.push_back(n2.x); dados.push_back(n2.y); dados.push_back(n2.z); }
        }
    }
    Tri_esfera = (int)dados.size() / 18;
    Vao_esfera = montaVAO(dados);
}

// -----------------------------
// Transformações e Camera
// -----------------------------

void transformacaoGenerica(float Tx, float Ty, float Tz, float Sx, float Sy, float Sz, float Rx, float Ry, float Rz) {
    glm::mat4 model = glm::translate(glm::mat4(1.0f), glm::vec3(Tx, Ty, Tz));
    model = glm::rotate(model, glm::radians(Rz), glm::vec3(0, 0, 1));
    model = glm::rotate(model, glm::radians(Ry), glm::vec3(0, 1, 0));
    model = glm::rotate(model, glm::radians(Rx), glm::vec3(1, 0, 0));
    model = glm::scale(model, glm::vec3(Sx, Sy, Sz));
    glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "transform"), 1, GL_FALSE, glm::value_ptr(model));
}

void especificaMatrizVisualizacao() {
    glm::vec3 front;
    front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front.y = sin(glm::radians(Cam_pitch));
    front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front = glm::normalize(front);
    glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + front, glm::vec3(0, 1, 0));
    glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "view"), 1, GL_FALSE, glm::value_ptr(view));
}

void especificaMatrizProjecao() {
    glm::mat4 proj = glm::perspective(glm::radians(67.0f), (float)WIDTH / HEIGHT, 0.1f, 100.0f);
    glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "proj"), 1, GL_FALSE, glm::value_ptr(proj));
}

// -----------------------------
// Loop e Callbacks
// -----------------------------

void trataTeclado() {
    float vel = Cam_speed * (float)Tempo_entre_frames;
    glm::vec3 front;
    front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front.y = sin(glm::radians(Cam_pitch));
    front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front = glm::normalize(front);
    glm::vec3 right = glm::normalize(glm::cross(front, glm::vec3(0, 1, 0)));

    if (glfwGetKey(Window, GLFW_KEY_W) == GLFW_PRESS) Cam_pos += front * vel;
    if (glfwGetKey(Window, GLFW_KEY_S) == GLFW_PRESS) Cam_pos -= front * vel;
    if (glfwGetKey(Window, GLFW_KEY_A) == GLFW_PRESS) Cam_pos -= right * vel;
    if (glfwGetKey(Window, GLFW_KEY_D) == GLFW_PRESS) Cam_pos += right * vel;
    if (glfwGetKey(Window, GLFW_KEY_ESCAPE) == GLFW_PRESS) glfwSetWindowShouldClose(Window, true);
}

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mode) {
    if (action != GLFW_PRESS) return;
    if (key == GLFW_KEY_EQUAL || key == GLFW_KEY_KP_ADD) {
        Resolucao_esfera = std::min(Resolucao_esfera + 2, 64);
        inicializaEsfera();
    }
    if (key == GLFW_KEY_MINUS || key == GLFW_KEY_KP_SUBTRACT) {
        Resolucao_esfera = std::max(Resolucao_esfera - 2, 4);
        inicializaEsfera();
    }
    if (key == GLFW_KEY_F) {
        Wireframe = !Wireframe;
        glPolygonMode(GL_FRONT_AND_BACK, Wireframe ? GL_LINE : GL_FILL);
    }
}

void redimensionaCallback(GLFWwindow* window, int w, int h) { WIDTH = w; HEIGHT = h; glViewport(0, 0, w, h); }
void mouse_callback(GLFWwindow* window, double xpos, double ypos) {
    if (primeiro_mouse) { lastX = xpos; lastY = ypos; primeiro_mouse = false; }
    float xoff = (float)(xpos - lastX); float yoff = (float)(lastY - ypos); lastX = xpos; lastY = ypos;
    Cam_yaw += xoff * 0.1f; Cam_pitch += yoff * 0.1f;
    if (Cam_pitch > 89.0f) Cam_pitch = 89.0f; if (Cam_pitch < -89.0f) Cam_pitch = -89.0f;
}

void defineCor(float r, float g, float b, float a) {
    glUniform4f(glGetUniformLocation(Shader_programm, "corobjeto"), r, g, b, a);
}

void atualizaHUD(double fps) {
    int total = Tri_cubo + Tri_piramide + Tri_esfera;
    std::cout << "\r[Res. esfera: " << std::setw(2) << Resolucao_esfera << "] Tri: " << total << " | FPS: " << std::fixed << std::setprecision(1) << fps << "    " << std::flush;
}

void inicializaRenderizacao() {
    glEnable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    double tempo_anterior = glfwGetTime();
    _fps_timer = tempo_anterior;

    while (!glfwWindowShouldClose(Window)) {
        double tempo_atual = glfwGetTime();
        Tempo_entre_frames = tempo_atual - tempo_anterior;
        tempo_anterior = tempo_atual;

        glClearColor(0.15f, 0.15f, 0.2f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glUseProgram(Shader_programm);
        especificaMatrizVisualizacao();
        especificaMatrizProjecao();

        float ang_luz = (float)tempo_atual * 0.8f;
        glm::vec3 luz_dir = glm::normalize(glm::vec3(cos(ang_luz), 0.6f, sin(ang_luz)));
        glUniform3fv(glGetUniformLocation(Shader_programm, "luz_dir"), 1, glm::value_ptr(luz_dir));

        glBindVertexArray(Vao_cubo); defineCor(0.3f, 0.6f, 1.0f, 1.0f);
        transformacaoGenerica(-2.5, 0, 0, 1, 1, 1, 20, 30, 0);
        glDrawArrays(GL_TRIANGLES, 0, Tri_cubo * 3);

        glBindVertexArray(Vao_piramide); defineCor(1.0f, 0.6f, 0.2f, 1.0f);
        transformacaoGenerica(0, 0, 0, 1, 1, 1, 0, 20, 0);
        glDrawArrays(GL_TRIANGLES, 0, Tri_piramide * 3);

        glBindVertexArray(Vao_esfera); defineCor(0.3f, 0.9f, 0.5f, 1.0f);
        transformacaoGenerica(2.5, 0, 0, 1, 1, 1, 0, 0, 0);
        glDrawArrays(GL_TRIANGLES, 0, Tri_esfera * 3);

        glfwPollEvents();
        glfwSwapBuffers(Window);
        trataTeclado();

        _fps_frames++;
        _fps_acumulado += (Tempo_entre_frames > 0) ? (1.0 / Tempo_entre_frames) : 0;
        if (tempo_atual - _fps_timer >= 1.0) {
            atualizaHUD(_fps_acumulado / _fps_frames);
            _fps_frames = 0; _fps_acumulado = 0; _fps_timer = tempo_atual;
        }
    }
}

// -----------------------------
// Função Principal
// -----------------------------

void inicializaOpenGL() {
    glfwInit();
    Window = glfwCreateWindow(WIDTH, HEIGHT, "Malha Interativa (GLAD + Modern GL)", NULL, NULL);
    glfwMakeContextCurrent(Window);
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) { std::cout << "Falha GLAD" << std::endl; exit(-1); }
    glfwSetWindowSizeCallback(Window, redimensionaCallback);
    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetKeyCallback(Window, key_callback);
}

int main() {
    inicializaOpenGL();
    inicializaShaders();
    inicializaCubo();
    inicializaPiramide();
    inicializaEsfera();
    inicializaRenderizacao();
    glfwTerminate();
    return 0;
}