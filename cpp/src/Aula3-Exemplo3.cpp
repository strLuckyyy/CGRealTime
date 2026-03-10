/* Terreno com Nível de Detalhe Ajustável — exemplo para a disciplina de Computação Gráfica em Tempo Real
 * * Este exemplo demonstra como a resolução de uma malha afeta diretamente
 * a qualidade visual de uma superfície curva gerada proceduralmente.
 *
 * Bibliotecas: GLAD, GLFW, GLM
 */

#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>

// GLAD
#include <glad/glad.h>
// GLFW
#include <GLFW/glfw3.h>
// GLM
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

using namespace std;

// -----------------------------
// Configuração geral
// -----------------------------

int WIDTH = 1000;
int HEIGHT = 700;

GLFWwindow* Window = nullptr;
GLuint Shader_programm;

// Câmera FPS
glm::vec3 Cam_pos = glm::vec3(0.0f, 4.0f, 10.0f);
float Cam_yaw = -90.0f;   // Aponta para o interior da cena (eixo -Z)
float Cam_pitch = -25.0f; // Inclina levemente para baixo para focar o terreno
float Cam_speed = 8.0f;

double lastX = 500, lastY = 350;
bool primeiro_mouse = true;
double Tempo_entre_frames = 0.0;

// -----------------------------
// Estado do terreno
// -----------------------------

int Resolucao_terreno = 10;
GLuint Vao_terreno = 0;
GLuint Vbo_terreno = 0;
GLuint Ebo_terreno = 0;
int Qtd_indices = 0;

// -----------------------------
// Protótipos
// -----------------------------
void inicializaTerreno();
void inicializaShaders();

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

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mode) {
    if (action != GLFW_PRESS) return;

    // + — aumenta o detalhe do terreno
    if (key == GLFW_KEY_EQUAL || key == GLFW_KEY_KP_ADD) {
        if (Resolucao_terreno < 200) {
            Resolucao_terreno += 5;
            inicializaTerreno();
            cout << "\n[TERRENO] Resolução: " << Resolucao_terreno << "x" << Resolucao_terreno 
                 << " -> " << Qtd_indices / 3 << " triângulos" << endl;
        }
    }

    // - — diminui o detalhe do terreno
    if (key == GLFW_KEY_MINUS || key == GLFW_KEY_KP_SUBTRACT) {
        if (Resolucao_terreno > 5) {
            Resolucao_terreno -= 5;
            inicializaTerreno();
            cout << "\n[TERRENO] Resolução: " << Resolucao_terreno << "x" << Resolucao_terreno 
                 << " -> " << Qtd_indices / 3 << " triângulos" << endl;
        }
    }
}

// -----------------------------
// Função de altura do terreno
// -----------------------------

float altura(float x, float z) {
    /* Define a altura do terreno em cada ponto (x, z).
     * O relevo emerge da avaliação desta função. */
    return (
        sin(x * 0.6f) * 1.5f +
        cos(z * 0.4f) * 1.2f +
        sin((x + z) * 0.3f) * 1.0f
    );
}

// -----------------------------
// Geração da malha do terreno
// -----------------------------

void geraTerreno(int res, vector<float>& vertices, vector<unsigned int>& indices) {
    float tamanho = 20.0f;
    float passo = tamanho / (float)res;

    // Amostragem da função de altura em cada ponto (i, j) do grid
    for (int i = 0; i <= res; i++) {
        for (int j = 0; j <= res; j++) {
            float x = -tamanho / 2.0f + j * passo;
            float z = -tamanho / 2.0f + i * passo;
            float y = altura(x, z);
            vertices.push_back(x);
            vertices.push_back(y);
            vertices.push_back(z);
        }
    }

    // Helper para converter grade 2D em índice linear
    auto idx = [&](int i, int j) { return i * (res + 1) + j; };

    // Divisão de cada célula quadrada em dois triângulos
    for (int i = 0; i < res; i++) {
        for (int j = 0; j < res; j++) {
            unsigned int a = idx(i, j);
            unsigned int b = idx(i + 1, j);
            unsigned int c = idx(i + 1, j + 1);
            unsigned int d = idx(i, j + 1);

            // Triângulo 1
            indices.push_back(a); indices.push_back(b); indices.push_back(c);
            // Triângulo 2
            indices.push_back(a); indices.push_back(c); indices.push_back(d);
        }
    }
}

void inicializaTerreno() {
    /* Cria (ou recria) o VAO/VBO/EBO do terreno com a resolução atual. */
    if (Vao_terreno != 0) {
        glDeleteVertexArrays(1, &Vao_terreno);
        glDeleteBuffers(1, &Vbo_terreno);
        glDeleteBuffers(1, &Ebo_terreno);
    }

    vector<float> vertices;
    vector<unsigned int> indices;
    geraTerreno(Resolucao_terreno, vertices, indices);
    Qtd_indices = (int)indices.size();

    glGenVertexArrays(1, &Vao_terreno);
    glGenBuffers(1, &Vbo_terreno);
    glGenBuffers(1, &Ebo_terreno);

    glBindVertexArray(Vao_terreno);

    glBindBuffer(GL_ARRAY_BUFFER, Vbo_terreno);
    glBufferData(GL_ARRAY_BUFFER, vertices.size() * sizeof(float), vertices.data(), GL_STATIC_DRAW);

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, Ebo_terreno);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.size() * sizeof(unsigned int), indices.data(), GL_STATIC_DRAW);

    // Atributo 0: posição (x, y, z)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    glBindVertexArray(0);

    string title = "Terreno — resolução " + to_string(Resolucao_terreno) + "x" + to_string(Resolucao_terreno);
    glfwSetWindowTitle(Window, title.c_str());
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
        void main() {
            frag_colour = vec4(0.3, 0.7, 0.4, 1.0);
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
// Inicialização OpenGL e Loop
// -----------------------------

int main() {
    if (!glfwInit()) return -1;
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    Window = glfwCreateWindow(WIDTH, HEIGHT, "Terreno procedural", NULL, NULL);
    if (!Window) { glfwTerminate(); return -1; }

    glfwMakeContextCurrent(Window);
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) return -1;

    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetKeyCallback(Window, key_callback);

    inicializaShaders();
    inicializaTerreno();

    glEnable(GL_DEPTH_TEST);

    double tempo_anterior = glfwGetTime();

    while (!glfwWindowShouldClose(Window)) {
        double tempo_atual = glfwGetTime();
        Tempo_entre_frames = tempo_atual - tempo_anterior;
        tempo_anterior = tempo_atual;

        glClearColor(0.5f, 0.75f, 1.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glUseProgram(Shader_programm);

        // Matrizes de Câmera (Uso de GLM para LookAt e Projeção)
        glm::vec3 frente;
        frente.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
        frente.y = sin(glm::radians(Cam_pitch));
        frente.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
        frente = glm::normalize(frente);

        glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + frente, glm::vec3(0.0f, 1.0f, 0.0f));
        glm::mat4 proj = glm::perspective(glm::radians(67.0f), (float)WIDTH / (float)HEIGHT, 0.1f, 200.0f);

        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "view"), 1, GL_FALSE, glm::value_ptr(view));
        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "proj"), 1, GL_FALSE, glm::value_ptr(proj));

        // Desenho do terreno
        glBindVertexArray(Vao_terreno);
        glDrawElements(GL_TRIANGLES, Qtd_indices, GL_UNSIGNED_INT, 0);

        // Input de movimento
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