// LOD Dinâmico com Distância - exemplo para a disciplina de Computação Gráfica em Tempo Real
//
// Este exemplo demonstra Level of Detail (LOD): usar versões diferentes da mesma
// malha conforme a distância da câmera, equilibrando qualidade visual e desempenho.
//
// Controles:
//   W/A/S/D     - mover câmera (FPS)
//   Mouse       - girar câmera
//   L           - alternar LOD automático ON/OFF (força LOD 0 quando OFF)
//   F           - alternar wireframe
//   ESC         - fechar
//
// HUD no terminal (a cada ~1 segundo):
//   LOD automático, triângulos ativos, distribuição LOD0/1/2, FPS médio

#include <iostream>
#include <vector>
#include <map>
#include <string>
#include <algorithm>
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

using namespace std;

// -----------------------------
// Estruturas e Globais
// -----------------------------

struct EsferaLOD {
    GLuint vao;
    int vertex_count;
};

GLFWwindow* Window = nullptr;
GLuint Shader_programm = 0;

int WIDTH = 800;
int HEIGHT = 600;
float Tempo_entre_frames = 0.0f;

// Câmera
float Cam_speed = 15.0f;
glm::vec3 Cam_pos(0.0f, 2.0f, 20.0f);
float Cam_yaw = 180.0f;
float Cam_pitch = -10.0f;
double lastX = WIDTH / 2.0, lastY = HEIGHT / 2.0;
bool primeiro_mouse = true;

// Estado
bool LOD_automatico = true;
bool Wireframe = false;
float LIMIAR_LOD_0 = 12.0f;
float LIMIAR_LOD_1 = 30.0f;

EsferaLOD Vaos_esferas[3];
vector<glm::vec3> Esferas_pos;
const int NUM_ESFERAS = 64;

// HUD
float _fps_acumulado = 0;
int _fps_frames = 0;
double _fps_timer = 0.0;

// -----------------------------
// Callbacks
// -----------------------------

void redimensionaCallback(GLFWwindow* window, int w, int h) {
    WIDTH = w; HEIGHT = h;
    glViewport(0, 0, w, h);
}

void mouse_callback(GLFWwindow* window, double xpos, double ypos) {
    if (primeiro_mouse) { lastX = xpos; lastY = ypos; primeiro_mouse = false; }
    float xoffset = (float)(xpos - lastX);
    float yoffset = (float)(lastY - ypos);
    lastX = xpos; lastY = ypos;

    float sensibilidade = 0.1f;
    Cam_yaw += xoffset * sensibilidade;
    Cam_pitch += yoffset * sensibilidade;
    Cam_pitch = glm::clamp(Cam_pitch, -89.0f, 89.0f);
}

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mods) {
    if (action != GLFW_PRESS) return;

    if (key == GLFW_KEY_L) {
        LOD_automatico = !LOD_automatico;
        cout << "\n[LOD] " << (LOD_automatico ? "AUTOMATICO" : "FORCADO LOD 0") << endl;
    }
    if (key == GLFW_KEY_F) {
        Wireframe = !Wireframe;
        glPolygonMode(GL_FRONT_AND_BACK, Wireframe ? GL_LINE : GL_FILL);
        cout << "\n[WIREFRAME] " << (Wireframe ? "ON" : "OFF") << endl;
    }
}

// -----------------------------
// Geração Geometria (Icosfera)
// -----------------------------

int get_ponto_medio(int p1, int p2, vector<glm::vec3>& vertices, map<pair<int, int>, int>& cache) {
    pair<int, int> chave = make_pair(min(p1, p2), max(p1, p2));
    if (cache.count(chave)) return cache[chave];

    glm::vec3 meio = glm::normalize((vertices[p1] + vertices[p2]) * 0.5f);
    vertices.push_back(meio);
    int idx = (int)vertices.size() - 1;
    cache[chave] = idx;
    return idx;
}

vector<float> _gera_icosfera(int subdivisoes, float raio) {
    float t = (1.0f + sqrt(5.0f)) / 2.0f;
    vector<glm::vec3> verts = {
        glm::normalize(glm::vec3(-1, t, 0)),  glm::normalize(glm::vec3(1, t, 0)),
        glm::normalize(glm::vec3(-1, -t, 0)), glm::normalize(glm::vec3(1, -t, 0)),
        glm::normalize(glm::vec3(0, -1, t)),  glm::normalize(glm::vec3(0, 1, t)),
        glm::normalize(glm::vec3(0, -1, -t)), glm::normalize(glm::vec3(0, 1, -t)),
        glm::normalize(glm::vec3(t, 0, -1)),  glm::normalize(glm::vec3(t, 0, 1)),
        glm::normalize(glm::vec3(-t, 0, -1)), glm::normalize(glm::vec3(-t, 0, 1))
    };

    struct Face { int a, b, c; };
    vector<Face> faces = {
        {0,11,5},{0,5,1},{0,1,7},{0,7,10},{0,10,11},
        {1,5,9},{5,11,4},{11,10,2},{10,7,6},{7,1,8},
        {3,9,4},{3,4,2},{3,2,6},{3,6,8},{3,8,9},
        {4,9,5},{2,4,11},{6,2,10},{8,6,7},{9,8,1}
    };

    for (int i = 0; i < subdivisoes; i++) {
        vector<Face> novas_faces;
        map<pair<int, int>, int> cache;
        for (auto& f : faces) {
            int ab = get_ponto_medio(f.a, f.b, verts, cache);
            int bc = get_ponto_medio(f.b, f.c, verts, cache);
            int ca = get_ponto_medio(f.c, f.a, verts, cache);
            novas_faces.push_back({f.a, ab, ca});
            novas_faces.push_back({f.b, bc, ab});
            novas_faces.push_back({f.c, ca, bc});
            novas_faces.push_back({ab, bc, ca});
        }
        faces = novas_faces;
    }

    vector<float> data;
    for (auto& f : faces) {
        glm::vec3 v1 = verts[f.a] * raio;
        glm::vec3 v2 = verts[f.b] * raio;
        glm::vec3 v3 = verts[f.c] * raio;
        data.insert(data.end(), {v1.x, v1.y, v1.z, v2.x, v2.y, v2.z, v3.x, v3.y, v3.z});
    }
    return data;
}

void inicializaEsferas() {
    for (int i = 0; i < 3; i++) {
        vector<float> verts = _gera_icosfera(3 - i, 0.8f);
        glGenVertexArrays(1, &Vaos_esferas[i].vao);
        glBindVertexArray(Vaos_esferas[i].vao);
        GLuint vbo;
        glGenBuffers(1, &vbo);
        glBindBuffer(GL_ARRAY_BUFFER, vbo);
        glBufferData(GL_ARRAY_BUFFER, verts.size() * sizeof(float), verts.data(), GL_STATIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, (void*)0);
        glEnableVertexAttribArray(0);
        Vaos_esferas[i].vertex_count = (int)verts.size() / 3;
    }

    int lado = (int)ceil(sqrt(NUM_ESFERAS));
    for (int i = 0; i < NUM_ESFERAS; i++) {
        float tx = (i % lado - lado / 2.0f) * 5.0f;
        float tz = (i / lado - lado / 2.0f) * 5.0f;
        Esferas_pos.push_back(glm::vec3(tx, 0.0f, tz));
    }
}

// -----------------------------
// Renderização e Shaders
// -----------------------------

void inicializaShaders() {
    const char* vs_src = "#version 450\n layout(location=0) in vec3 pos; uniform mat4 transform, view, proj; void main(){ gl_Position = proj * view * transform * vec4(pos,1.0); }";
    const char* fs_src = "#version 450\n out vec4 color; uniform vec4 corobjeto; void main(){ color = corobjeto; }";
    
    auto compile = [](const char* src, GLenum type) {
        GLuint s = glCreateShader(type);
        glShaderSource(s, 1, &src, nullptr);
        glCompileShader(s);
        return s;
    };
    GLuint vs = compile(vs_src, GL_VERTEX_SHADER);
    GLuint fs = compile(fs_src, GL_FRAGMENT_SHADER);
    Shader_programm = glCreateProgram();
    glAttachShader(Shader_programm, vs);
    glAttachShader(Shader_programm, fs);
    glLinkProgram(Shader_programm);
}

void renderizaCena(int& total_tri, int* cont_lod) {
    for (auto& pos : Esferas_pos) {
        float dist = glm::distance(Cam_pos, pos);
        int lod = !LOD_automatico ? 0 : (dist < LIMIAR_LOD_0 ? 0 : (dist < LIMIAR_LOD_1 ? 1 : 2));

        glm::mat4 model = glm::translate(glm::mat4(1.0f), pos);
        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "transform"), 1, GL_FALSE, glm::value_ptr(model));

        glm::vec4 cores[] = { {0.3,0.6,1,1}, {0.3,0.9,0.4,1}, {1,0.6,0.2,1} };
        glUniform4fv(glGetUniformLocation(Shader_programm, "corobjeto"), 1, glm::value_ptr(cores[lod]));

        glBindVertexArray(Vaos_esferas[lod].vao);
        glDrawArrays(GL_TRIANGLES, 0, Vaos_esferas[lod].vertex_count);

        cont_lod[lod]++;
        total_tri += Vaos_esferas[lod].vertex_count / 3;
    }
}

int main() {
    glfwInit();
    Window = glfwCreateWindow(WIDTH, HEIGHT, "Exemplo LOD - C++", nullptr, nullptr);
    glfwMakeContextCurrent(Window);
    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);
    
    glfwSetFramebufferSizeCallback(Window, redimensionaCallback);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetKeyCallback(Window, key_callback);
    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);

    inicializaShaders();
    inicializaEsferas();
    glEnable(GL_DEPTH_TEST);

    while (!glfwWindowShouldClose(Window)) {
        float t = (float)glfwGetTime();
        Tempo_entre_frames = t - (float)_fps_timer; // Simplificado para o loop

        glClearColor(0.12f, 0.12f, 0.18f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glUseProgram(Shader_programm);
        
        // Câmera e Projeção
        glm::vec3 front;
        front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
        front.y = sin(glm::radians(Cam_pitch));
        front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
        glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + glm::normalize(front), glm::vec3(0,1,0));
        glm::mat4 proj = glm::perspective(glm::radians(67.0f), (float)WIDTH/HEIGHT, 0.1f, 300.0f);
        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "view"), 1, GL_FALSE, glm::value_ptr(view));
        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "proj"), 1, GL_FALSE, glm::value_ptr(proj));

        int total_tri = 0, cont_lod[3] = {0,0,0};
        renderizaCena(total_tri, cont_lod);

        if (t - _fps_timer >= 1.0) {
            printf("\r[LOD %s] Tri: %7d | LOD0(azul): %2d | LOD1(verde): %2d | LOD2(laranja): %2d | FPS: %5.1f", 
                LOD_automatico ? "AUTO" : "LOD0", total_tri, cont_lod[0], cont_lod[1], cont_lod[2], _fps_frames/(t-_fps_timer));
            fflush(stdout);
            _fps_timer = t; _fps_frames = 0;
        }
        _fps_frames++;

        glfwSwapBuffers(Window);
        glfwPollEvents();
        
        // Trata Teclado Simples
        float vel = Cam_speed * 0.016f; // fixo para exemplo
        glm::vec3 f = glm::normalize(front);
        glm::vec3 r = glm::normalize(glm::cross(f, glm::vec3(0,1,0)));
        if(glfwGetKey(Window, GLFW_KEY_W)) Cam_pos += f * vel;
        if(glfwGetKey(Window, GLFW_KEY_S)) Cam_pos -= f * vel;
        if(glfwGetKey(Window, GLFW_KEY_A)) Cam_pos -= r * vel;
        if(glfwGetKey(Window, GLFW_KEY_D)) Cam_pos += r * vel;
    }

    glfwTerminate();
    return 0;
}