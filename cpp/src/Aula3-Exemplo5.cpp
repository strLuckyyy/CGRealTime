/* Bounding Volume (AABB) vs Malha Real — exemplo para a disciplina de Computação Gráfica em Tempo Real
 *
 * Este exemplo demonstra a diferença entre a malha real de um objeto
 * e uma geometria auxiliar chamada Bounding Volume (volume delimitador).
 *
 * Malha real: define a forma exata (Esfera UV), usada para renderização.
 * AABB: caixa alinhada aos eixos que envolve o objeto, usada para colisões rápidas.
 */

#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// -----------------------------
// Configuração geral
// -----------------------------

int WIDTH = 1000;
int HEIGHT = 700;

GLFWwindow* Window = nullptr;
GLuint Shader_programm;

// Câmera FPS
glm::vec3 Cam_pos = glm::vec3(0.0f, 0.0f, 4.0f);
float Cam_yaw = -90.0f;
float Cam_pitch = 0.0f;
float Cam_speed = 4.0f;

double lastX = 500, lastY = 350;
bool primeiro_mouse = true;
double Tempo_entre_frames = 0.0;

// Estado dos objetos
GLuint Vao_esfera, Ebo_esfera;
int Qtd_indices_esfera = 0;

GLuint Vao_aabb, Ebo_aabb;
int Qtd_indices_aabb = 0;

// -----------------------------
// Callbacks
// -----------------------------

void mouse_callback(GLFWwindow* window, double xpos, double ypos) {
    if (primeiro_mouse) {
        lastX = xpos; lastY = ypos;
        primeiro_mouse = false;
    }
    float xoffset = (float)(xpos - lastX);
    float yoffset = (float)(lastY - ypos);
    lastX = xpos; lastY = ypos;

    float sensibilidade = 0.1f;
    Cam_yaw += xoffset * sensibilidade;
    Cam_pitch += yoffset * sensibilidade;

    if (Cam_pitch > 89.0f) Cam_pitch = 89.0f;
    if (Cam_pitch < -89.0f) Cam_pitch = -89.0f;
}

// -----------------------------
// Geometria
// -----------------------------

void geraEsferaUV(int stacks, int slices, float raio, vector<float>& vertices, vector<unsigned int>& indices) {
    /* Gera uma esfera UV parametrizada por phi (vertical) e theta (horizontal). */
    for (int i = 0; i <= stacks; ++i) {
        float phi = (float)M_PI * i / stacks;
        for (int j = 0; j <= slices; ++j) {
            float theta = 2.0f * (float)M_PI * j / slices;
            float x = raio * sin(phi) * cos(theta);
            float y = raio * cos(phi);
            float z = raio * sin(phi) * sin(theta);
            vertices.push_back(x); vertices.push_back(y); vertices.push_back(z);
        }
    }

    auto get_idx = [&](int i, int j) { return i * (slices + 1) + j; };

    for (int i = 0; i < stacks; ++i) {
        for (int j = 0; j < slices; ++j) {
            unsigned int a = get_idx(i, j);
            unsigned int b = get_idx(i + 1, j);
            unsigned int c = get_idx(i + 1, j + 1);
            unsigned int d = get_idx(i, j + 1);
            indices.push_back(a); indices.push_back(b); indices.push_back(c);
            indices.push_back(a); indices.push_back(c); indices.push_back(d);
        }
    }
}

void calculaAABB(const vector<float>& vertices, glm::vec3& min_v, glm::vec3& max_v) {
    /* Calcula o menor paralelepípedo alinhado aos eixos que contém a malha. */
    min_v = glm::vec3(vertices[0], vertices[1], vertices[2]);
    max_v = min_v;

    for (size_t i = 0; i < vertices.size(); i += 3) {
        min_v.x = min(min_v.x, vertices[i]);
        min_v.y = min(min_v.y, vertices[i + 1]);
        min_v.z = min(min_v.z, vertices[i + 2]);

        max_v.x = max(max_v.x, vertices[i]);
        max_v.y = max(max_v.y, vertices[i + 1]);
        max_v.z = max(max_v.z, vertices[i + 2]);
    }
}

void inicializaGeometria() {
    vector<float> v_esfera;
    vector<unsigned int> i_esfera;
    geraEsferaUV(48, 48, 0.8f, v_esfera, i_esfera);
    Qtd_indices_esfera = (int)i_esfera.size();

    glm::vec3 min_v, max_v;
    calculaAABB(v_esfera, min_v, max_v);

    // VAO Esfera
    glGenVertexArrays(1, &Vao_esfera);
    glBindVertexArray(Vao_esfera);
    GLuint vbo_e, ebo_e;
    glGenBuffers(1, &vbo_e);
    glBindBuffer(GL_ARRAY_BUFFER, vbo_e);
    glBufferData(GL_ARRAY_BUFFER, v_esfera.size() * sizeof(float), v_esfera.data(), GL_STATIC_DRAW);
    glGenBuffers(1, &ebo_e);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_e);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, i_esfera.size() * sizeof(unsigned int), i_esfera.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    // VAO AABB (Wireframe)
    float v_aabb[] = {
        min_v.x, min_v.y, min_v.z, // 0
        max_v.x, min_v.y, min_v.z, // 1
        max_v.x, max_v.y, min_v.z, // 2
        min_v.x, max_v.y, min_v.z, // 3
        min_v.x, min_v.y, max_v.z, // 4
        max_v.x, min_v.y, max_v.z, // 5
        max_v.x, max_v.y, max_v.z, // 6
        min_v.x, max_v.y, max_v.z  // 7
    };
    unsigned int i_aabb[] = {
        0,1, 1,2, 2,3, 3,0, // trás
        4,5, 5,6, 6,7, 7,4, // frente
        0,4, 1,5, 2,6, 3,7  // laterais
    };
    Qtd_indices_aabb = 24;

    glGenVertexArrays(1, &Vao_aabb);
    glBindVertexArray(Vao_aabb);
    GLuint vbo_a, ebo_a;
    glGenBuffers(1, &vbo_a);
    glBindBuffer(GL_ARRAY_BUFFER, vbo_a);
    glBufferData(GL_ARRAY_BUFFER, sizeof(v_aabb), v_aabb, GL_STATIC_DRAW);
    glGenBuffers(1, &ebo_a);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_a);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(i_aabb), i_aabb, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    glBindVertexArray(0);
}

// -----------------------------
// Shaders
// -----------------------------

void inicializaShaders() {
    const char* vertex_shader = R"(
        #version 330 core
        layout(location = 0) in vec3 vertex_posicao;
        uniform mat4 view, proj;
        void main() {
            gl_Position = proj * view * vec4(vertex_posicao, 1.0);
        }
    )";

    const char* fragment_shader = R"(
        #version 330 core
        out vec4 frag_colour;
        uniform vec4 corobjeto;
        void main() {
            frag_colour = corobjeto;
        }
    )";

    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &vertex_shader, NULL);
    glCompileShader(vs);

    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &fragment_shader, NULL);
    glCompileShader(fs);

    Shader_programm = glCreateProgram();
    glAttachShader(Shader_programm, vs);
    glAttachShader(Shader_programm, fs);
    glLinkProgram(Shader_programm);
    glDeleteShader(vs); glDeleteShader(fs);
}

// -----------------------------
// Loop de renderização
// -----------------------------

int main() {
    if (!glfwInit()) return -1;
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    Window = glfwCreateWindow(WIDTH, HEIGHT, "AABB vs Malha Real", NULL, NULL);
    if (!Window) { glfwTerminate(); return -1; }

    glfwMakeContextCurrent(Window);
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) return -1;

    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(Window, mouse_callback);

    inicializaShaders();
    inicializaGeometria();

    glEnable(GL_DEPTH_TEST);

    cout << "\n--- Exemplo: Bounding Volume (AABB) vs Malha Real ---" << endl;
    cout << "  Azul     - esfera UV (malha real, solido)" << endl;
    cout << "  Vermelho - AABB (wireframe): aproximacao retangular" << endl;

    double tempo_anterior = glfwGetTime();

    while (!glfwWindowShouldClose(Window)) {
        double tempo_atual = glfwGetTime();
        Tempo_entre_frames = tempo_atual - tempo_anterior;
        tempo_anterior = tempo_atual;

        glClearColor(0.15f, 0.18f, 0.22f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glUseProgram(Shader_programm);

        // Câmera
        glm::vec3 frente;
        frente.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
        frente.y = sin(glm::radians(Cam_pitch));
        frente.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
        frente = glm::normalize(frente);

        glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + frente, glm::vec3(0.0f, 1.0f, 0.0f));
        glm::mat4 proj = glm::perspective(glm::radians(67.0f), (float)WIDTH/HEIGHT, 0.1f, 100.0f);

        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "view"), 1, GL_FALSE, glm::value_ptr(view));
        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "proj"), 1, GL_FALSE, glm::value_ptr(proj));

        GLint colorLoc = glGetUniformLocation(Shader_programm, "corobjeto");

        // --- Esfera (Malha Real) ---
        glUniform4f(colorLoc, 0.3f, 0.7f, 0.9f, 1.0f);
        glBindVertexArray(Vao_esfera);
        glDrawElements(GL_TRIANGLES, Qtd_indices_esfera, GL_UNSIGNED_INT, 0);

        // --- AABB (Volume Delimitador) ---
        glUniform4f(colorLoc, 1.0f, 0.2f, 0.2f, 1.0f);
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE); // Wireframe
        glBindVertexArray(Vao_aabb);
        glDrawElements(GL_LINES, Qtd_indices_aabb, GL_UNSIGNED_INT, 0);
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL); // Restaura sólido

        // Movimento FPS
        float vel = Cam_speed * (float)Tempo_entre_frames;
        glm::vec3 direita = glm::normalize(glm::cross(frente, glm::vec3(0.0f, 1.0f, 0.0f)));
        if (glfwGetKey(Window, GLFW_KEY_W) == GLFW_PRESS) Cam_pos += frente * vel;
        if (glfwGetKey(Window, GLFW_KEY_S) == GLFW_PRESS) Cam_pos -= frente * vel;
        if (glfwGetKey(Window, GLFW_KEY_A) == GLFW_PRESS) Cam_pos -= direita * vel;
        if (glfwGetKey(Window, GLFW_KEY_D) == GLFW_PRESS) Cam_pos += direita * vel;
        if (glfwGetKey(Window, GLFW_KEY_ESCAPE) == GLFW_PRESS) glfwSetWindowShouldClose(Window, true);

        glfwSwapBuffers(Window);
        glfwPollEvents();
    }

    glfwTerminate();
    return 0;
}