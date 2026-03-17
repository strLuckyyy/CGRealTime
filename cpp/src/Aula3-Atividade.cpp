/* 
    Exercício: Construir um Anel 3D (Toroide)

    Controles:
        W/A/S/D                 — mover câmera (FPS)
        Mouse                   — girar câmera
        ESC                     — fechar

        ↑, ↓                    — aumentar/diminuir resolução do toroide
        ←, →                    — aumentar/diminuir tamanho dos pontos
        1                       — alternar exibição de pontos
        2                       — alternar exibição de wireframe
    
    by: Abrahão Francis Gonçalves
 */

#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#include <iostream>
#include <vector>
#include <string>
#include <cmath>

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
double lastFrame = 0.0;

GLuint vaoTeroide;

// Exibição
int resolucao = 35;
int tamPontos = 5;
bool exibirPontos = false;
bool exibirLinhas = false;

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
// Geometria do Teroide
// -----------------------------

vector<float> gerarGeometria(int resolucao) {
    vector<float> vbo_teroide;
    float R = 3;
    float r = .5f;

    float phi, theta = 0.f;
    float x, y, z = 0.f;
    glm::vec3 normal, c;

    for(int i = 0; i < resolucao; i++){
        phi = (float)i * (2 * M_PI / resolucao);
        for(int j = 0; j < resolucao; j++){
            theta = (float)j * (2 * M_PI / resolucao);

            //posição
            x = (R + r * cosf(theta)) * cosf(phi);
            y = r * sinf(theta);
            z = (R + r * cosf(theta)) * sinf(phi);

            //normal
            c = glm::vec3(R * cosf(phi), 0, R * sinf(phi));
            normal = glm::vec3(x, y, z) - glm::vec3(c[0], c[1], c[2]);
            normal = glm::normalize(normal);

            vbo_teroide.push_back(x);
            vbo_teroide.push_back(y);
            vbo_teroide.push_back(z);
            vbo_teroide.push_back(normal.x);
            vbo_teroide.push_back(normal.y);
            vbo_teroide.push_back(normal.z);
        }
    }
    return vbo_teroide;
}

vector<unsigned int> gerarMalha(int resolucao) {
    vector<unsigned int> ebo;
    unsigned int p1, p2, p3, p4 = 0;

    for(int i = 0; i < resolucao; i++){
        for(int j = 0; j < resolucao; j++){
            p1 = i * resolucao + j;
            p2 = ((i + 1) % resolucao) * resolucao + j;
            p3 = i * resolucao + ((j + 1) % resolucao);
            p4 = ((i + 1) % resolucao) * resolucao + ((j + 1) % resolucao);

            //T1
            ebo.push_back(p1);
            ebo.push_back(p2);
            ebo.push_back(p3);

            //T2
            ebo.push_back(p2);
            ebo.push_back(p4);
            ebo.push_back(p3);
        }
    }

    return ebo;
}

void inicializaGeometria() {
    const vector<float> vboTeroide = gerarGeometria(resolucao);
    const vector<unsigned int> vboMalha = gerarMalha(resolucao);

    unsigned int stride = 6 * sizeof(float);

    glGenVertexArrays(1, &vaoTeroide);
    glBindVertexArray(vaoTeroide);

    GLuint vbo, ebo;
    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, vboTeroide.size() * sizeof(float), vboTeroide.data(), GL_STATIC_DRAW);

    glGenBuffers(1, &ebo);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, vboMalha.size() * sizeof(unsigned int), vboMalha.data(), GL_STATIC_DRAW);

    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, (void*)0);
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, (void*)(3 * sizeof(float)));
}

// -----------------------------
// Shaders
// -----------------------------

void inicializaShaders() {
    const char* vertex_shader = R"(
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        layout(location = 1) in vec3 vertex_normal;
 
        uniform mat4 transform, view, proj;
        out vec3 normal_mundo;

        void main () {
            gl_Position  = proj * view * transform * vec4(vertex_posicao, 1.0);
            
            // Transforma a normal para o espaço do mundo usando apenas a parte
            // rotação/escala da matriz de transformação (ignora translação)
            
            normal_mundo = mat3(transform) * vertex_normal;
        }
    )";

    const char* fragment_shader = R"(
        #version 400
        in  vec3 normal_mundo;
        out vec4 frag_colour;
        uniform vec4 corobjeto;
        uniform vec3 luz_dir;  // direção da luz orbital — atualizada pelo Python a cada frame

        void main () {
            vec3  n           = normalize(normal_mundo);
            float difuso      = max(dot(n, luz_dir), 0.0) * 0.8;
            float ambiente    = 0.2;
            float intensidade = difuso + ambiente;
            frag_colour = vec4(corobjeto.rgb * intensidade, corobjeto.a);
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
// Teclado
// -----------------------------

void keyboardHandle(){
    float vel = Cam_speed * Tempo_entre_frames;
    double tempo_atual = glfwGetTime();
    double cd = 0.2;

    glm::vec3 frente;
    frente.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente.y = sin(glm::radians(Cam_pitch));
    frente.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente = glm::normalize(frente);

    glm::vec3 direita = glm::normalize(glm::cross(frente, glm::vec3(0.0f, 1.0f, 0.0f)));

    // Entrada WASD
    if (glfwGetKey(Window, GLFW_KEY_W) == GLFW_PRESS) Cam_pos += frente * vel;
    if (glfwGetKey(Window, GLFW_KEY_S) == GLFW_PRESS) Cam_pos -= frente * vel;
    if (glfwGetKey(Window, GLFW_KEY_A) == GLFW_PRESS) Cam_pos -= direita * vel;
    if (glfwGetKey(Window, GLFW_KEY_D) == GLFW_PRESS) Cam_pos += direita * vel;
    
    // Sair do programa
    if (glfwGetKey(Window, GLFW_KEY_ESCAPE) == GLFW_PRESS) glfwSetWindowShouldClose(Window, true);

    if (tempo_atual - lastFrame > cd) {
        bool mudou = false;

        // Resolução
        if (glfwGetKey(Window, GLFW_KEY_UP) == GLFW_PRESS) { resolucao += 5; mudou = true; }
        if (glfwGetKey(Window, GLFW_KEY_DOWN) == GLFW_PRESS) { resolucao -= 5; mudou = true; }
        
        // Toggles
        if (glfwGetKey(Window, GLFW_KEY_1) == GLFW_PRESS) { exibirPontos = !exibirPontos; mudou = true; }
        if (glfwGetKey(Window, GLFW_KEY_2) == GLFW_PRESS) { exibirLinhas = !exibirLinhas; mudou = true; }
        
        // Tamanho dos pontos
        if (glfwGetKey(Window, GLFW_KEY_RIGHT) == GLFW_PRESS) { tamPontos += 1; mudou = true; }
        if (glfwGetKey(Window, GLFW_KEY_LEFT) == GLFW_PRESS) { tamPontos -= 1; mudou = true; }

        if (mudou) {
            if (resolucao < 5) resolucao = 5;
            inicializaGeometria();
            lastFrame = tempo_atual;
        }
    }
}
    
// -----------------------------
// Loop de renderização
// -----------------------------

int main() {
    if (!glfwInit()) return -1;
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    Window = glfwCreateWindow(WIDTH, HEIGHT, "Teroide", NULL, NULL);
    if (!Window) { glfwTerminate(); return -1; }

    glfwMakeContextCurrent(Window);
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) return -1;

    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(Window, mouse_callback);

    inicializaShaders();
    inicializaGeometria();

    glEnable(GL_DEPTH_TEST);

    double tempo_anterior = glfwGetTime();

    cout << "\n\n  W/A/S/D + mouse - camera FPS" << endl;
    cout << "  ESC             - fechar\n" << endl;
    cout << "  ^, v            - aumentar/diminuir resolucao do toroide" << endl;
    cout << "  <, >            - aumentar/diminuir tamanho dos pontos" << endl;
    cout << "  1               - alternar exibicao de pontos" << endl;
    cout << "  2               - alternar exibicao de wireframe" << endl;

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

        // Iluminação
        float angulo_luz = (float)glfwGetTime() * .8f;
        float luz_x = cosf(angulo_luz);
        float luz_z = sinf(angulo_luz);
        glm::vec3 luz_dir = glm::normalize(glm::vec3(luz_x, .6f, luz_z));
        glUniform3fv(glGetUniformLocation(Shader_programm, "luz_dir"), 1, glm::value_ptr(luz_dir));

        // Desenha o teroide
        glUniformMatrix4fv(transLoc, 1, GL_TRUE, glm::value_ptr(glm::mat4(1.0f)));
        glBindVertexArray(vaoTeroide);

        // Exibir pontos
        if (exibirPontos) {
            glUniform4f(colorLoc, .0f, .0f, 1.0f, 1.0f);
            glPointSize(tamPontos);
            glDrawArrays(GL_POINTS, 0, resolucao * resolucao);
        }

        // Exibir wireframe ou sólido
        if (exibirLinhas) {
            glUniform4f(colorLoc, 1.0f, 1.0f, 1.0f, 1.0f);
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
        }
        else {
            glUniform4f(colorLoc, 1.0f, 0.5f, 0.0f, 1.0f);
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
        }

        glDrawElements(GL_TRIANGLES, resolucao * resolucao * 6, GL_UNSIGNED_INT, 0);

        glfwSwapBuffers(Window);
        glfwPollEvents();
        keyboardHandle();
    }

    glfwTerminate();
    return 0;
}