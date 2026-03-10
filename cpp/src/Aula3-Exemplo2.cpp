/* Normais de Face vs. Normais de Vértice — exemplo para a disciplina de Computação Gráfica em Tempo Real
 * * Este exemplo demonstra a diferença visual entre dois tipos de normais geométricas:
 *
 * Normal de Face:
 * - Um único vetor normal por triângulo, perpendicular ao plano da face
 * - Todos os vértices do triângulo compartilham a mesma normal
 * - Resultado visual: aparência FACETADA — cada face tem brilho uniforme e distinto
 *
 * Normal de Vértice:
 * - Cada vértice recebe a média das normais das faces ao redor
 * - A normal é INTERPOLADA pelo rasterizador entre os vértices do triângulo
 * - Resultado visual: aparência SUAVE — transição gradual de brilho entre faces
 */

#include <iostream>
#include <string>
#include <vector>
#include <cmath>
#include <iomanip>
#include <map>

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

// Um VAO por objeto por modo
GLuint Vao_cubo_face, Vao_cubo_vertice;
GLuint Vao_pir_face, Vao_pir_vertice;
GLuint Vao_esf_face, Vao_esf_vertice;

int WIDTH = 800, HEIGHT = 600;
double Tempo_entre_frames = 0;

// Câmera
float Cam_speed = 8.0f;
glm::vec3 Cam_pos = glm::vec3(0.0f, 0.5f, 7.0f);
float Cam_yaw = -90.0f, Cam_pitch = -4.0f;
double lastX = 400, lastY = 300;
bool primeiro_mouse = true;

// Estado da demonstração
bool Modo_normal_vertice = false;
int Resolucao_esfera = 8;
int Tri_cubo = 0, Tri_piramide = 0, Tri_esfera = 0;
bool Wireframe = false;

// FPS
double _fps_acumulado = 0.0;
int _fps_frames = 0;
double _fps_timer = 0.0;

// -----------------------------
// Shaders
// -----------------------------

void inicializaShaders() {
    const GLchar* vertexShaderSource = R"(
        #version 450
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec3 normal;
        uniform mat4 transform, view, proj;
        out vec3 normal_mundo;
        void main() {
            gl_Position = proj * view * transform * vec4(position, 1.0);
            normal_mundo = mat3(transform) * normal;
        }
    )";

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
            frag_colour = vec4(corobjeto.rgb * (difuso + ambiente), corobjeto.a);
        }
    )";

    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &vertexShaderSource, NULL);
    glCompileShader(vs);

    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &fragmentShaderSource, NULL);
    glCompileShader(fs);

    Shader_programm = glCreateProgram();
    glAttachShader(Shader_programm, vs);
    glAttachShader(Shader_programm, fs);
    glLinkProgram(Shader_programm);
    glDeleteShader(vs); glDeleteShader(fs);
}

// -----------------------------
// Utilitários de Geometria
// -----------------------------

glm::vec3 calculaNormal(glm::vec3 v0, glm::vec3 v1, glm::vec3 v2) {
    glm::vec3 a = v1 - v0;
    glm::vec3 b = v2 - v0;
    glm::vec3 n = glm::cross(a, b);
    if (glm::length(n) < 1e-8) return glm::vec3(0.0f, 1.0f, 0.0f);
    return glm::normalize(n);
}

GLuint montaVAO(const std::vector<float>& dados) {
    GLuint VBO, VAO;
    glGenVertexArrays(1, &VAO);
    glGenBuffers(1, &VBO);
    glBindVertexArray(VAO);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, dados.size() * sizeof(float), dados.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);
    return VAO;
}

// -----------------------------
// Cubo: Face e Vértice
// -----------------------------

void inicializaCubo() {
    struct FaceData { std::vector<glm::vec3> v; glm::vec3 n; };
    std::vector<FaceData> faces = {
        {{{-0.5,-0.5, 0.5},{ 0.5,-0.5, 0.5},{ 0.5, 0.5, 0.5},{-0.5, 0.5, 0.5}}, { 0, 0, 1}},
        {{{ 0.5,-0.5,-0.5},{-0.5,-0.5,-0.5},{-0.5, 0.5,-0.5},{ 0.5, 0.5,-0.5}}, { 0, 0,-1}},
        {{{ 0.5,-0.5, 0.5},{ 0.5,-0.5,-0.5},{ 0.5, 0.5,-0.5},{ 0.5, 0.5, 0.5}}, { 1, 0, 0}},
        {{{-0.5,-0.5,-0.5},{-0.5,-0.5, 0.5},{-0.5, 0.5, 0.5},{-0.5, 0.5,-0.5}}, {-1, 0, 0}},
        {{{-0.5, 0.5, 0.5},{ 0.5, 0.5, 0.5},{ 0.5, 0.5,-0.5},{-0.5, 0.5,-0.5}}, { 0, 1, 0}},
        {{{-0.5,-0.5,-0.5},{ 0.5,-0.5,-0.5},{ 0.5,-0.5, 0.5},{-0.5,-0.5, 0.5}}, { 0,-1, 0}}
    };

    // FACE
    std::vector<float> d_face;
    for (auto& f : faces) {
        int idx[] = {0, 1, 2, 0, 2, 3};
        for (int i : idx) {
            d_face.push_back(f.v[i].x); d_face.push_back(f.v[i].y); d_face.push_back(f.v[i].z);
            d_face.push_back(f.n.x);    d_face.push_back(f.n.y);    d_face.push_back(f.n.z);
        }
    }
    Tri_cubo = d_face.size() / 18;
    Vao_cubo_face = montaVAO(d_face);

    // VÉRTICE (Média das normais)
    std::map<std::string, std::vector<glm::vec3>> normais_por_v;
    for (auto& f : faces) {
        for (auto& v : f.v) {
            char key[64]; sprintf(key, "%.3f%.3f%.3f", v.x, v.y, v.z);
            normais_por_v[key].push_back(f.n);
        }
    }

    std::vector<float> d_vert;
    for (auto& f : faces) {
        int idx[] = {0, 1, 2, 0, 2, 3};
        for (int i : idx) {
            d_vert.push_back(f.v[i].x); d_vert.push_back(f.v[i].y); d_vert.push_back(f.v[i].z);
            char key[64]; sprintf(key, "%.3f%.3f%.3f", f.v[i].x, f.v[i].y, f.v[i].z);
            glm::vec3 media(0);
            for(auto& n : normais_por_v[key]) media += n;
            media = glm::normalize(media);
            d_vert.push_back(media.x); d_vert.push_back(media.y); d_vert.push_back(media.z);
        }
    }
    Vao_cubo_vertice = montaVAO(d_vert);
}

// -----------------------------
// Pirâmide
// -----------------------------

void inicializaPiramide() {
    glm::vec3 topo(0.0, 0.8, 0.0), ffd(-0.5, -0.4, 0.5), ffe(0.5, -0.4, 0.5), tfd(-0.5, -0.4, -0.5), tfe(0.5, -0.4, -0.5);
    std::vector<std::vector<glm::vec3>> tris = { {topo, ffd, ffe}, {topo, ffe, tfe}, {topo, tfe, tfd}, {topo, tfd, ffd}, {ffd, tfd, tfe}, {ffd, tfe, ffe} };

    // FACE
    std::vector<float> d_face;
    for (auto& t : tris) {
        glm::vec3 n = calculaNormal(t[0], t[1], t[2]);
        for (int i = 0; i < 3; i++) {
            d_face.push_back(t[i].x); d_face.push_back(t[i].y); d_face.push_back(t[i].z);
            d_face.push_back(n.x);    d_face.push_back(n.y);    d_face.push_back(n.z);
        }
    }
    Tri_piramide = d_face.size() / 18;
    Vao_pir_face = montaVAO(d_face);

    // VÉRTICE
    std::map<std::string, std::vector<glm::vec3>> normais_por_v;
    for (auto& t : tris) {
        glm::vec3 n = calculaNormal(t[0], t[1], t[2]);
        for (int i = 0; i < 3; i++) {
            char key[64]; sprintf(key, "%.3f%.3f%.3f", t[i].x, t[i].y, t[i].z);
            normais_por_v[key].push_back(n);
        }
    }

    std::vector<float> d_vert;
    for (auto& t : tris) {
        for (int i = 0; i < 3; i++) {
            d_vert.push_back(t[i].x); d_vert.push_back(t[i].y); d_vert.push_back(t[i].z);
            char key[64]; sprintf(key, "%.3f%.3f%.3f", t[i].x, t[i].y, t[i].z);
            glm::vec3 media(0);
            for(auto& n : normais_por_v[key]) media += n;
            media = glm::normalize(media);
            d_vert.push_back(media.x); d_vert.push_back(media.y); d_vert.push_back(media.z);
        }
    }
    Vao_pir_vertice = montaVAO(d_vert);
}

// -----------------------------
// Esfera (Caso Dramático)
// -----------------------------

void inicializaEsfera() {
    int rings = Resolucao_esfera, sectors = Resolucao_esfera;
    float raio = 0.8f;
    std::vector<float> d_face, d_vert;

    for (int r = 0; r < rings; r++) {
        for (int s = 0; s < sectors; s++) {
            float t0 = M_PI * r / rings, t1 = M_PI * (r + 1) / rings;
            float p0 = 2 * M_PI * s / sectors, p1 = 2 * M_PI * (s + 1) / sectors;

            auto getV = [&](float t, float p) { return glm::vec3(sin(t)*cos(p), cos(t), sin(t)*sin(p)) * raio; };
            glm::vec3 v00 = getV(t0, p0), v01 = getV(t0, p1), v10 = getV(t1, p0), v11 = getV(t1, p1);

            // Normais de Vértice (Radial na Esfera)
            auto getN = [&](glm::vec3 v) { return glm::length(v) > 1e-8 ? glm::normalize(v) : glm::vec3(0,1,0); };
            glm::vec3 nv[] = {getN(v00), getN(v01), getN(v10), getN(v11)};

            // Triângulo 1
            glm::vec3 nf1 = calculaNormal(v00, v10, v11);
            glm::vec3 tri1[] = {v00, v10, v11};
            glm::vec3 nvi1[] = {nv[0], nv[2], nv[3]};
            for(int i=0; i<3; i++){
                d_face.push_back(tri1[i].x); d_face.push_back(tri1[i].y); d_face.push_back(tri1[i].z); d_face.push_back(nf1.x); d_face.push_back(nf1.y); d_face.push_back(nf1.z);
                d_vert.push_back(tri1[i].x); d_vert.push_back(tri1[i].y); d_vert.push_back(tri1[i].z); d_vert.push_back(nvi1[i].x); d_vert.push_back(nvi1[i].y); d_vert.push_back(nvi1[i].z);
            }
            // Triângulo 2
            glm::vec3 nf2 = calculaNormal(v00, v11, v01);
            glm::vec3 tri2[] = {v00, v11, v01};
            glm::vec3 nvi2[] = {nv[0], nv[3], nv[1]};
            for(int i=0; i<3; i++){
                d_face.push_back(tri2[i].x); d_face.push_back(tri2[i].y); d_face.push_back(tri2[i].z); d_face.push_back(nf2.x); d_face.push_back(nf2.y); d_face.push_back(nf2.z);
                d_vert.push_back(tri2[i].x); d_vert.push_back(tri2[i].y); d_vert.push_back(tri2[i].z); d_vert.push_back(nvi2[i].x); d_vert.push_back(nvi2[i].y); d_vert.push_back(nvi2[i].z);
            }
        }
    }
    Tri_esfera = d_face.size() / 18;
    Vao_esf_face = montaVAO(d_face);
    Vao_esf_vertice = montaVAO(d_vert);
}

// -----------------------------
// Callbacks e Loop
// -----------------------------

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mode) {
    if (action != GLFW_PRESS) return;
    if (key == GLFW_KEY_N) Modo_normal_vertice = !Modo_normal_vertice;
    if (key == GLFW_KEY_EQUAL || key == GLFW_KEY_KP_ADD) { Resolucao_esfera = min(Resolucao_esfera + 2, 64); inicializaEsfera(); }
    if (key == GLFW_KEY_MINUS || key == GLFW_KEY_KP_SUBTRACT) { Resolucao_esfera = max(Resolucao_esfera - 2, 4); inicializaEsfera(); }
    if (key == GLFW_KEY_F) { Wireframe = !Wireframe; glPolygonMode(GL_FRONT_AND_BACK, Wireframe ? GL_LINE : GL_FILL); }
    if (key == GLFW_KEY_ESCAPE) glfwSetWindowShouldClose(Window, true);
}

void redimensionaCallback(GLFWwindow* window, int w, int h) { WIDTH = w; HEIGHT = h; glViewport(0, 0, w, h); }
void mouse_callback(GLFWwindow* window, double xpos, double ypos) {
    if (primeiro_mouse) { lastX = xpos; lastY = ypos; primeiro_mouse = false; }
    float xoff = (float)(xpos - lastX); float yoff = (float)(lastY - ypos); lastX = xpos; lastY = ypos;
    Cam_yaw += xoff * 0.1f; Cam_pitch += yoff * 0.1f;
    if (Cam_pitch > 89.0f) Cam_pitch = 89.0f; if (Cam_pitch < -89.0f) Cam_pitch = -89.0f;
}

void inicializaRenderizacao() {
    glEnable(GL_DEPTH_TEST); glEnable(GL_BLEND);
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
        
        // Câmera LookAt
        glm::vec3 front;
        front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
        front.y = sin(glm::radians(Cam_pitch));
        front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
        front = glm::normalize(front);
        glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + front, glm::vec3(0, 1, 0));
        glm::mat4 proj = glm::perspective(glm::radians(67.0f), (float)WIDTH/HEIGHT, 0.1f, 100.0f);
        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "view"), 1, GL_FALSE, glm::value_ptr(view));
        glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "proj"), 1, GL_FALSE, glm::value_ptr(proj));

        // Luz Orbital
        float ang_luz = (float)tempo_atual * 0.8f;
        glm::vec3 luz_dir = glm::normalize(glm::vec3(cos(ang_luz), 0.6f, sin(ang_luz)));
        glUniform3fv(glGetUniformLocation(Shader_programm, "luz_dir"), 1, glm::value_ptr(luz_dir));

        // Seleção de VAO
        GLuint v_cubo = Modo_normal_vertice ? Vao_cubo_vertice : Vao_cubo_face;
        GLuint v_pir  = Modo_normal_vertice ? Vao_pir_vertice : Vao_pir_face;
        GLuint v_esf  = Modo_normal_vertice ? Vao_esf_vertice : Vao_esf_face;

        glBindVertexArray(v_cubo); glUniform4f(glGetUniformLocation(Shader_programm, "corobjeto"), 0.3f, 0.6f, 1.0f, 1.0f);
        transformacaoGenerica(-2.5, 0, 0, 1, 1, 1, 20, 30, 0);
        glDrawArrays(GL_TRIANGLES, 0, Tri_cubo * 3);

        glBindVertexArray(v_pir); glUniform4f(glGetUniformLocation(Shader_programm, "corobjeto"), 1.0f, 0.6f, 0.2f, 1.0f);
        transformacaoGenerica(0, 0, 0, 1, 1, 1, 0, 20, 0);
        glDrawArrays(GL_TRIANGLES, 0, Tri_piramide * 3);

        glBindVertexArray(v_esf); glUniform4f(glGetUniformLocation(Shader_programm, "corobjeto"), 0.3f, 0.9f, 0.5f, 1.0f);
        transformacaoGenerica(2.5, 0, 0, 1, 1, 1, 0, 0, 0);
        glDrawArrays(GL_TRIANGLES, 0, Tri_esfera * 3);

        glfwPollEvents(); glfwSwapBuffers(Window);
        
        // Movimento Camera
        float vel = 8.0f * (float)Tempo_entre_frames;
        glm::vec3 right = glm::normalize(glm::cross(front, glm::vec3(0, 1, 0)));
        if (glfwGetKey(Window, GLFW_KEY_W) == GLFW_PRESS) Cam_pos += front * vel;
        if (glfwGetKey(Window, GLFW_KEY_S) == GLFW_PRESS) Cam_pos -= front * vel;
        if (glfwGetKey(Window, GLFW_KEY_A) == GLFW_PRESS) Cam_pos -= right * vel;
        if (glfwGetKey(Window, GLFW_KEY_D) == GLFW_PRESS) Cam_pos += right * vel;

        _fps_frames++; _fps_acumulado += (Tempo_entre_frames > 0) ? (1.0 / Tempo_entre_frames) : 0;
        if (tempo_atual - _fps_timer >= 1.0) {
            atualizaHUD(_fps_acumulado / _fps_frames);
            _fps_frames = 0; _fps_acumulado = 0; _fps_timer = tempo_atual;
        }
    }
}

void transformacaoGenerica(float Tx, float Ty, float Tz, float Sx, float Sy, float Sz, float Rx, float Ry, float Rz) {
    glm::mat4 m = glm::translate(glm::mat4(1.0f), glm::vec3(Tx, Ty, Tz));
    m = glm::rotate(m, glm::radians(Rz), glm::vec3(0,0,1));
    m = glm::rotate(m, glm::radians(Ry), glm::vec3(0,1,0));
    m = glm::rotate(m, glm::radians(Rx), glm::vec3(1,0,0));
    m = glm::scale(m, glm::vec3(Sx, Sy, Sz));
    glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "transform"), 1, GL_FALSE, glm::value_ptr(m));
}

void atualizaHUD(double fps) {
    cout << "\r[Normal: " << (Modo_normal_vertice ? "VÉRTICE" : "FACE   ") << "] "
         << "Res: " << setw(2) << Resolucao_esfera << " | FPS: " << fixed << setprecision(1) << fps << "   " << flush;
}

int main() {
    glfwInit();
    Window = glfwCreateWindow(WIDTH, HEIGHT, "Normal de Face vs Vértice (GLAD)", NULL, NULL);
    glfwMakeContextCurrent(Window);
    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);
    glfwSetKeyCallback(Window, key_callback);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    
    inicializaShaders();
    inicializaCubo();
    inicializaPiramide();
    inicializaEsfera();
    inicializaRenderizacao();
    
    glfwTerminate();
    return 0;
}