/* Cubo com e sem Índice — exemplo para a disciplina de Computação Gráfica em Tempo Real
 * * Este exemplo demonstra que o mesmo objeto (um cubo) pode ser representado
 * de duas formas diferentes na GPU:
 *
 * 1) Sem índice — glDrawArrays:
 * - cada triângulo declara seus próprios três vértices
 * - cubo com 36 vértices no VBO (muita redundância)
 *
 * 2) Com índice — glDrawElements:
 * - cada posição única é armazenada apenas uma vez (8 vértices no total)
 * - um buffer de índices (EBO) define a conectividade
 */

#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#include <iostream>
#include <vector>
#include <string>

using namespace std;

// -----------------------------
// Configuração geral
// -----------------------------

int WIDTH = 1000;
int HEIGHT = 700;

GLFWwindow* Window = nullptr;
GLuint Shader_programm;

// Câmera FPS
glm::vec3 Cam_pos = glm::vec3(0.0f, 1.5f, 6.0f);
float Cam_yaw = -90.0f;
float Cam_pitch = -10.0f;
float Cam_speed = 5.0f;

double lastX = 500, lastY = 350;
bool primeiro_mouse = true;
double Tempo_entre_frames = 0.0;

// Estado dos objetos
GLuint Vao_sem_indice;
GLuint Vao_com_indice;

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
// Geometria do cubo
// -----------------------------

void inicializaGeometria() {
    // -------- Cubo sem índice (glDrawArrays) --------
    // 36 vértices (6 faces * 2 triângulos * 3 vértices)
    float vertices_sem[] = {
        // frente
        -1,-1, 1,  1,-1, 1,  1, 1, 1,  -1,-1, 1,  1, 1, 1, -1, 1, 1,
        // trás
        -1,-1,-1, -1, 1,-1,  1, 1,-1,  -1,-1,-1,  1, 1,-1,  1,-1,-1,
        // esquerda
        -1,-1,-1, -1,-1, 1, -1, 1, 1,  -1,-1,-1, -1, 1, 1, -1, 1,-1,
        // direita
         1,-1,-1,  1, 1,-1,  1, 1, 1,   1,-1,-1,  1, 1, 1,  1,-1, 1,
        // superior
        -1, 1,-1, -1, 1, 1,  1, 1, 1,  -1, 1,-1,  1, 1, 1,  1, 1,-1,
        // inferior
        -1,-1,-1,  1,-1,-1,  1,-1, 1,  -1,-1,-1,  1,-1, 1, -1,-1, 1
    };

    glGenVertexArrays(1, &Vao_sem_indice);
    glBindVertexArray(Vao_sem_indice);
    GLuint vbo_sem;
    glGenBuffers(1, &vbo_sem);
    glBindBuffer(GL_ARRAY_BUFFER, vbo_sem);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices_sem), vertices_sem, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    // -------- Cubo com índice (glDrawElements) --------
    // Apenas 8 vértices únicos
    float vertices_com[] = {
        -1,-1, 1,   // 0
         1,-1, 1,   // 1
         1, 1, 1,   // 2
        -1, 1, 1,   // 3
        -1,-1,-1,   // 4
         1,-1,-1,   // 5
         1, 1,-1,   // 6
        -1, 1,-1    // 7
    };

    unsigned int indices[] = {
        0,1,2,  0,2,3,   // frontal
        4,7,6,  4,6,5,   // traseira
        4,0,3,  4,3,7,   // esquerda
        1,5,6,  1,6,2,   // direita
        3,2,6,  3,6,7,   // superior
        4,5,1,  4,1,0    // inferior
    };

    glGenVertexArrays(1, &Vao_com_indice);
    glBindVertexArray(Vao_com_indice);
    
    GLuint vbo_com, ebo;
    glGenBuffers(1, &vbo_com);
    glBindBuffer(GL_ARRAY_BUFFER, vbo_com);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices_com), vertices_com, GL_STATIC_DRAW);

    glGenBuffers(1, &ebo);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(indices), indices, GL_STATIC_DRAW);

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
        uniform mat4 transform, view, proj;
        void main() {
            gl_Position = proj * view * transform * vec4(vertex_posicao, 1.0);
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

    Window = glfwCreateWindow(WIDTH, HEIGHT, "Cubo com e sem Índice", NULL, NULL);
    if (!Window) { glfwTerminate(); return -1; }

    glfwMakeContextCurrent(Window);
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) return -1;

    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(Window, mouse_callback);

    inicializaShaders();
    inicializaGeometria();

    glEnable(GL_DEPTH_TEST);

    double tempo_anterior = glfwGetTime();

    cout << "\n--- Exemplo: Cubo com e sem Indice ---" << endl;
    cout << "  Vermelho (esquerda) - sem indice: 36 vertices, glDrawArrays" << endl;
    cout << "  Verde    (direita)  - com indice:  8 vertices + EBO, glDrawElements" << endl;

    while (!glfwWindowShouldClose(Window)) {
        double tempo_atual = glfwGetTime();
        Tempo_entre_frames = tempo_atual - tempo_anterior;
        tempo_anterior = tempo_atual;

        glClearColor(0.2f, 0.3f, 0.4f, 1.0f);
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

        GLint transLoc = glGetUniformLocation(Shader_programm, "transform");
        GLint colorLoc = glGetUniformLocation(Shader_programm, "corobjeto");

        // --- Cubo sem índice (Esquerda) ---
        glUniform4f(colorLoc, 0.9f, 0.4f, 0.4f, 1.0f);
        glm::mat4 modelSem = glm::translate(glm::mat4(1.0f), glm::vec3(-2.0f, 0.0f, 0.0f));
        glUniformMatrix4fv(transLoc, 1, GL_FALSE, glm::value_ptr(modelSem));
        glBindVertexArray(Vao_sem_indice);
        glDrawArrays(GL_TRIANGLES, 0, 36);

        // --- Cubo com índice (Direita) ---
        glUniform4f(colorLoc, 0.4f, 0.9f, 0.4f, 1.0f);
        glm::mat4 modelCom = glm::translate(glm::mat4(1.0f), glm::vec3(2.0f, 0.0f, 0.0f));
        glUniformMatrix4fv(transLoc, 1, GL_FALSE, glm::value_ptr(modelCom));
        glBindVertexArray(Vao_com_indice);
        glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_INT, 0);

        // Entrada WASD
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