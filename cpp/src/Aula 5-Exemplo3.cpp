#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>
#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>
#include <random>

// Debug Visual do Frustum Culling — exemplo para a disciplina de Computação Gráfica em Tempo Real
//
// Este exemplo é uma extensão didática do Exemplo 4 (Frustum Culling).
// O objetivo aqui não é mostrar o ganho de desempenho, mas tornar o culling
// VISÍVEL — responder à pergunta: "o que exatamente está sendo descartado?"
//
// Novidades em relação ao Exemplo 4:
// - Câmera de jogo (Cam_jogo) separada da câmera de debug (Cam_debug):
//     A câmera de jogo pode ser TRAVADA no lugar (tecla T).
//     Com ela travada, você pilota a câmera de debug ao redor da cena e
//     enxerga o frustum da câmera de jogo como um objeto no mundo.
// - Wireframe amarelo do frustum:
//     As 12 arestas da pirâmide truncada (frustum) são desenhadas no espaço do mundo.
//     Qualquer cubo fora desse volume está sendo descartado.
// - Objetos culled em vermelho semitransparente:
//     Cubos fora do frustum são desenhados em vermelho translúcido (modo raio-x),
//     revelando o que normalmente seria invisível — e portanto descartado.
//
// Controles:
//   W/A/S/D + Mouse  — mover câmera ATIVA (jogo ou debug, dependendo do modo)
//   T                — travar/destravar câmera de jogo (ativa câmera de debug)
//   C                — alternar frustum culling (objetos culled ficam vermelhos ou somem)
//   +/-              — mais/menos objetos na cena
//   ESC              — fechar
//
// HUD no terminal (a cada ~1 segundo):
//   Modo câmera, culling, objetos na cena, desenhados, culled, FPS

GLFWwindow* Window = nullptr;
GLuint Shader_programm = 0;
GLuint Vao_cubo = 0;
GLuint Vao_frustum = 0;  // VAO das arestas do wireframe do frustum
GLuint Vbo_frustum = 0;
int WIDTH = 800;
int HEIGHT = 600;

float Tempo_entre_frames = 0.0f;  // variavel utilizada para movimentar a camera

// -----------------------------
// Câmera de JOGO — é esta que define o frustum de culling
// -----------------------------
// Pode ser travada no lugar (Cam_jogo_travada = True).
// Quando travada, o frustum fica fixo no mundo e a câmera de debug orbita ao redor.

glm::vec3 Cam_jogo_pos = glm::vec3(0.0f, 0.0f, 30.0f);
float Cam_jogo_yaw = -90.0f;  // olhando para a cena (ajustado para o padrão GLM)
float Cam_jogo_pitch = 0.0f;
bool Cam_jogo_travada = false;  // False = câmera de jogo é a ativa; True = debug é a ativa

// -----------------------------
// Câmera de DEBUG — só fica ativa quando a câmera de jogo está travada
// -----------------------------
// Permite orbitar a cena e ver o frustum da câmera de jogo de fora.

glm::vec3 Cam_debug_pos = glm::vec3(0.0f, 20.0f, 60.0f);
float Cam_debug_yaw = -70.0f;
float Cam_debug_pitch = -15.0f;

// Variáveis compartilhadas de mouse (sempre referem à câmera ativa)
double lastX = 400.0, lastY = 300.0;
bool primeiro_mouse = true;

// Velocidade de movimento
float Cam_speed = 20.0f;  // velocidade da camera, 20 unidades por segundo

// Projeção — parâmetros globais usados tanto para a matriz de projeção
// quanto para extrair os planos e construir o wireframe do frustum
float Cam_fov = 67.0f;   // campo de visão em graus
float Cam_znear = 0.1f;    // plano de corte próximo
float Cam_zfar = 80.0f;   // plano de corte distante (reduzido para o frustum ser mais visível na cena)

// -----------------------------
// Estado da demonstração
// -----------------------------

// True  → frustum culling ativado (objetos culled ficam vermelhos semitransparentes)
// False → culling desativado (todos os objetos são desenhados em azul normalmente)
bool Frustum_culling_ativo = true;

// Número de objetos na cena
int Num_objetos = 150;

// Lista de posições dos objetos (gerada uma vez com seed fixa)
std::vector<glm::vec3> Objetos_posicoes;

// Raio do bounding volume de cada objeto (cubos unitários, raio = sqrt(3)/2)
float Bounding_raio = std::sqrt(3.0f) / 2.0f;

// Contadores do último frame
int Objetos_desenhados = 0;
int Objetos_culled = 0;

// Acumuladores de FPS para o HUD
float _fps_acumulado = 0.0f;
int _fps_frames = 0;
double _fps_timer = 0.0;

struct Plano {
    glm::vec3 normal;
    float d;
};

// Protótipos para organização
void geraObjetos();
void atualizaFrustumWireframe();

// -----------------------------
// Callbacks de janela e entrada
// -----------------------------

void redimensionaCallback(GLFWwindow* window, int w, int h) {
    WIDTH = w;
    HEIGHT = h;
}

void mouse_callback(GLFWwindow* window, double xpos, double ypos) {
    if (primeiro_mouse) {
        lastX = xpos;
        lastY = ypos;
        primeiro_mouse = false;
    }

    double xoffset = xpos - lastX;
    double yoffset = lastY - ypos;
    lastX = xpos;
    lastY = ypos;

    float sensibilidade = 0.1f;
    xoffset *= sensibilidade;
    yoffset *= sensibilidade;

    // O mouse controla a câmera ativa no momento
    if (!Cam_jogo_travada) {
        Cam_jogo_yaw += (float)xoffset;
        Cam_jogo_pitch += (float)yoffset;
        Cam_jogo_pitch = std::max(-89.0f, std::min(89.0f, Cam_jogo_pitch));
    } else {
        Cam_debug_yaw += (float)xoffset;
        Cam_debug_pitch += (float)yoffset;
        Cam_debug_pitch = std::max(-89.0f, std::min(89.0f, Cam_debug_pitch));
    }
}

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mode) {
    if (action != GLFW_PRESS) return;

    // T — trava/destrava a câmera de jogo
    if (key == GLFW_KEY_T) {
        Cam_jogo_travada = !Cam_jogo_travada;
        primeiro_mouse = true;  // reseta o mouse ao trocar de câmera (evita salto)
        const char* estado = Cam_jogo_travada ? "TRAVADA (câmera de debug ativa)" : "LIVRE (câmera de jogo ativa)";
        std::cout << "\n[CÂMERA] Câmera de jogo " << estado << std::endl;
        if (Cam_jogo_travada) {
            std::cout << "         -> Você agora vê o frustum da câmera de jogo no mundo!" << std::endl;
        }
    }

    // C — alterna frustum culling
    if (key == GLFW_KEY_C) {
        Frustum_culling_ativo = !Frustum_culling_ativo;
        const char* estado = Frustum_culling_ativo ? "ATIVADO (culled = vermelho)" : "DESATIVADO (tudo azul)";
        std::cout << "\n[CULLING] Frustum culling " << estado << std::endl;
    }

    // + / = — mais objetos
    if (key == GLFW_KEY_EQUAL || key == GLFW_KEY_KP_ADD) {
        Num_objetos = std::min(Num_objetos + 50, 2000);
        geraObjetos();
        std::cout << "\n[OBJETOS] " << Num_objetos << " objetos na cena" << std::endl;
    }

    // - — menos objetos
    if (key == GLFW_KEY_MINUS || key == GLFW_KEY_KP_SUBTRACT) {
        Num_objetos = std::max(Num_objetos - 50, 50);
        geraObjetos();
        std::cout << "\n[OBJETOS] " << Num_objetos << " objetos na cena" << std::endl;
    }
}

// -----------------------------
// Inicialização do OpenGL
// -----------------------------

void inicializaOpenGL() {
    if (!glfwInit()) exit(EXIT_FAILURE);
    Window = glfwCreateWindow(WIDTH, HEIGHT, "Debug Visual — Frustum Culling", NULL, NULL);
    if (!Window) { glfwTerminate(); exit(EXIT_FAILURE); }
    glfwMakeContextCurrent(Window);
    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);
    glfwSetWindowSizeCallback(Window, redimensionaCallback);
    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetKeyCallback(Window, key_callback);

    std::cout << "Placa de vídeo: " << glGetString(GL_RENDERER) << std::endl;
    std::cout << "Versão do OpenGL: " << glGetString(GL_VERSION) << std::endl;
}

// -----------------------------
// Inicialização da geometria: cubo unitário
// -----------------------------

void inicializaCubo() {
    glGenVertexArrays(1, &Vao_cubo);
    glBindVertexArray(Vao_cubo);
    float points[] = {
        0.5f, 0.5f, 0.5f,   0.5f, -0.5f, 0.5f,   -0.5f, -0.5f, 0.5f,
        -0.5f, 0.5f, 0.5f,  0.5f,  0.5f, 0.5f,   -0.5f, -0.5f, 0.5f,
        0.5f, 0.5f, -0.5f,  0.5f, -0.5f, -0.5f,  -0.5f, -0.5f, -0.5f,
        -0.5f, 0.5f, -0.5f, 0.5f,  0.5f, -0.5f,  -0.5f, -0.5f, -0.5f,
        -0.5f, -0.5f,  0.5f,  -0.5f,  0.5f,  0.5f,  -0.5f, -0.5f, -0.5f,
        -0.5f, -0.5f, -0.5f,  -0.5f,  0.5f, -0.5f,  -0.5f,  0.5f,  0.5f,
        0.5f, -0.5f,  0.5f,   0.5f,  0.5f,  0.5f,   0.5f, -0.5f, -0.5f,
        0.5f, -0.5f, -0.5f,   0.5f,  0.5f, -0.5f,   0.5f,  0.5f,  0.5f,
        -0.5f, -0.5f,  0.5f,  0.5f, -0.5f,  0.5f,   0.5f, -0.5f, -0.5f,
         0.5f, -0.5f, -0.5f, -0.5f, -0.5f, -0.5f,  -0.5f, -0.5f,  0.5f,
        -0.5f, 0.5f,  0.5f,   0.5f,  0.5f,  0.5f,   0.5f,  0.5f, -0.5f,
         0.5f, 0.5f, -0.5f,  -0.5f,  0.5f, -0.5f,  -0.5f,  0.5f,  0.5f,
    };
    GLuint vbo; glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(points), points, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, NULL);
}

// -----------------------------
// Cálculo dos 8 vértices do frustum no espaço do mundo
// -----------------------------
// O frustum é uma pirâmide truncada definida por dois retângulos:
// um pequeno (plano Near) e um grande (plano Far), centrados na direção 'front'.
//
// Os 8 vértices são calculados a partir dos vetores da câmera de JOGO
// (não da câmera de debug), pois é o frustum de jogo que queremos visualizar.
//
//   nlt, nrt, nlb, nrb = Near Left Top, Near Right Top, Near Left Bottom, Near Right Bottom
//   flt, frt, flb, frb = Far  Left Top, Far  Right Top, Far  Left Bottom, Far  Right Bottom

void calculaVerticesFrustum(glm::vec3* v) {
    float tang = std::tan(glm::radians(Cam_fov) / 2.0f);
    float hn = Cam_znear * tang;
    float wn = hn * ((float)WIDTH / HEIGHT);
    float hf = Cam_zfar * tang;
    float wf = hf * ((float)WIDTH / HEIGHT);

    glm::vec3 front;
    front.x = cos(glm::radians(Cam_jogo_yaw)) * cos(glm::radians(Cam_jogo_pitch));
    front.y = sin(glm::radians(Cam_jogo_pitch));
    front.z = sin(glm::radians(Cam_jogo_yaw)) * cos(glm::radians(Cam_jogo_pitch));
    front = glm::normalize(front);
    glm::vec3 right = glm::normalize(glm::cross(front, glm::vec3(0.0f, 1.0f, 0.0f)));
    glm::vec3 up = glm::cross(right, front);

    glm::vec3 cn = Cam_jogo_pos + front * Cam_znear;
    glm::vec3 cf = Cam_jogo_pos + front * Cam_zfar;

    v[0] = cn + up * hn - right * wn; // nlt
    v[1] = cn + up * hn + right * wn; // nrt
    v[2] = cn - up * hn - right * wn; // nlb
    v[3] = cn - up * hn + right * wn; // nrb
    v[4] = cf + up * hf - right * wf; // flt
    v[5] = cf + up * hf + right * wf; // frt
    v[6] = cf - up * hf - right * wf; // flb
    v[7] = cf - up * hf + right * wf; // frb
}

// -----------------------------
// Inicialização e atualização do VAO do wireframe do frustum
// -----------------------------
// O frustum é desenhado como 12 arestas em GL_LINES.
// Como o frustum muda a cada frame (câmera de jogo pode se mover),
// o VBO é atualizado dinamicamente via glBufferSubData.
//
// As 12 arestas são:
//   4 arestas do near plane  (quadrilátero frontal)
//   4 arestas do far plane   (quadrilátero traseiro)
//   4 arestas laterais ligando near ao far (as "bordas" do tronco)

void inicializaFrustumWireframe() {
    glGenVertexArrays(1, &Vao_frustum);
    glBindVertexArray(Vao_frustum);
    glGenBuffers(1, &Vbo_frustum);
    glBindBuffer(GL_ARRAY_BUFFER, Vbo_frustum);
    glBufferData(GL_ARRAY_BUFFER, 24 * 3 * sizeof(float), NULL, GL_DYNAMIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, NULL);
}

void atualizaFrustumWireframe() {
    glm::vec3 v[8];
    calculaVerticesFrustum(v);
    glm::vec3 arestas[] = {
        v[0],v[1], v[1],v[3], v[3],v[2], v[2],v[0], // Near
        v[4],v[5], v[5],v[7], v[7],v[6], v[6],v[4], // Far
        v[0],v[4], v[1],v[5], v[3],v[7], v[2],v[6]  // Laterais
    };
    glBindBuffer(GL_ARRAY_BUFFER, Vbo_frustum);
    glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(arestas), arestas);
}

// -----------------------------
// Shaders e Transformações
// -----------------------------

void inicializaShaders() {
    const char* vs_src = R"(#version 400
        layout(location=0) in vec3 pos; uniform mat4 transform, view, proj;
        void main() { gl_Position = proj*view*transform*vec4(pos,1.0); })";
    const char* fs_src = R"(#version 400
        out vec4 color; uniform vec4 corobjeto;
        void main() { color = corobjeto; })";

    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &vs_src, NULL); glCompileShader(vs);
    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &fs_src, NULL); glCompileShader(fs);
    Shader_programm = glCreateProgram();
    glAttachShader(Shader_programm, vs); glAttachShader(Shader_programm, fs);
    glLinkProgram(Shader_programm);
}

void transformacaoGenerica(glm::vec3 t, glm::vec3 s) {
    glm::mat4 m = glm::translate(glm::mat4(1.0f), t);
    m = glm::scale(m, s);
    glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "transform"), 1, GL_FALSE, glm::value_ptr(m));
}

// -----------------------------
// Câmeras: visualização e projeção
// -----------------------------

glm::mat4 montaMatrizView(glm::vec3 pos, float yaw, float pitch) {
    /**
    Monta e retorna a matriz de visualização (lookAt manual) para uma câmera
    definida por posição, yaw e pitch. Usada tanto para a câmera de jogo
    quanto para a câmera de debug.
    (Comentário lookAt omitido por brevidade técnica interna)
    */
    glm::vec3 f;
    f.x = cos(glm::radians(yaw)) * cos(glm::radians(pitch));
    f.y = sin(glm::radians(pitch));
    f.z = sin(glm::radians(yaw)) * cos(glm::radians(pitch));
    return glm::lookAt(pos, pos + glm::normalize(f), glm::vec3(0, 1, 0));
}

void especificaCamera() {
    glm::mat4 view = Cam_jogo_travada ? montaMatrizView(Cam_debug_pos, Cam_debug_yaw, Cam_debug_pitch) 
                                      : montaMatrizView(Cam_jogo_pos, Cam_jogo_yaw, Cam_jogo_pitch);
    float zf = Cam_jogo_travada ? 300.0f : Cam_zfar;
    glm::mat4 proj = glm::perspective(glm::radians(Cam_fov), (float)WIDTH/HEIGHT, Cam_znear, zf);
    
    glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "view"), 1, GL_FALSE, glm::value_ptr(view));
    glUniformMatrix4fv(glGetUniformLocation(Shader_programm, "proj"), 1, GL_FALSE, glm::value_ptr(proj));
}

// -----------------------------
// Extração dos 6 planos do frustum (câmera de JOGO)
// -----------------------------

std::vector<Plano> extraiPlanosFrustum() {
    glm::vec3 f;
    f.x = cos(glm::radians(Cam_jogo_yaw)) * cos(glm::radians(Cam_jogo_pitch));
    f.y = sin(glm::radians(Cam_jogo_pitch));
    f.z = sin(glm::radians(Cam_jogo_yaw)) * cos(glm::radians(Cam_jogo_pitch));
    f = glm::normalize(f);
    glm::vec3 r = glm::normalize(glm::cross(f, glm::vec3(0, 1, 0)));
    glm::vec3 u = glm::cross(r, f);

    float hf = Cam_zfar * std::tan(glm::radians(Cam_fov)/2.0f);
    float wf = hf * ((float)WIDTH/HEIGHT);

    std::vector<Plano> p;
    p.push_back({f, -glm::dot(f, Cam_jogo_pos + f * Cam_znear)}); // Near
    p.push_back({-f, glm::dot(f, Cam_jogo_pos + f * Cam_zfar)});  // Far
    
    glm::vec3 rn = glm::normalize(glm::cross(f * Cam_zfar - r * wf, u));
    p.push_back({rn, -glm::dot(rn, Cam_jogo_pos)}); // Right
    glm::vec3 ln = glm::normalize(glm::cross(u, f * Cam_zfar + r * wf));
    p.push_back({ln, -glm::dot(ln, Cam_jogo_pos)}); // Left
    glm::vec3 tn = glm::normalize(glm::cross(r, f * Cam_zfar - u * hf));
    p.push_back({tn, -glm::dot(tn, Cam_jogo_pos)}); // Top
    glm::vec3 bn = glm::normalize(glm::cross(f * Cam_zfar + u * hf, r));
    p.push_back({bn, -glm::dot(bn, Cam_jogo_pos)}); // Bottom
    return p;
}

// -----------------------------
// Teste de visibilidade: bounding sphere vs frustum
// -----------------------------

bool estaNoFrustum(glm::vec3 c, float r, const std::vector<Plano>& planos) {
    /**
    Retorna True se a bounding sphere (centro, raio) está dentro (ou intersecta) o frustum.
    Retorna False se está completamente fora de pelo menos um plano.
    */
    for(auto &p : planos) if(glm::dot(p.normal, c) + p.d < -r) return false;
    return true;
}

void geraObjetos() {
    Objetos_posicoes.clear();
    std::mt19937 rng(42);
    std::uniform_real_distribution<float> d(-40, 40);
    for(int i=0; i<Num_objetos; i++) Objetos_posicoes.push_back({d(rng), d(rng), d(rng)});
}

// -----------------------------
// Entrada de teclado
// -----------------------------

void trataTeclado() {
    /**
    Movimenta a câmera no espaço 3D conforme teclas WASD.
    Move a câmera ATIVA: câmera de jogo (modo normal) ou câmera de debug (modo travado).
    */
    float v = Cam_speed * Tempo_entre_frames;
    float y = Cam_jogo_travada ? Cam_debug_yaw : Cam_jogo_yaw;
    float p = Cam_jogo_travada ? Cam_debug_pitch : Cam_jogo_pitch;
    
    glm::vec3 f;
    f.x = cos(glm::radians(y)) * cos(glm::radians(p));
    f.y = sin(glm::radians(p));
    f.z = sin(glm::radians(y)) * cos(glm::radians(p));
    f = glm::normalize(f);
    glm::vec3 r = glm::normalize(glm::cross(f, glm::vec3(0,1,0)));

    glm::vec3 &pos = Cam_jogo_travada ? Cam_debug_pos : Cam_jogo_pos;
    if(glfwGetKey(Window, GLFW_KEY_W)) pos += f * v;
    if(glfwGetKey(Window, GLFW_KEY_S)) pos -= f * v;
    if(glfwGetKey(Window, GLFW_KEY_A)) pos -= r * v;
    if(glfwGetKey(Window, GLFW_KEY_D)) pos += r * v;
    if(glfwGetKey(Window, GLFW_KEY_ESCAPE)) glfwSetWindowShouldClose(Window, true);
}

void atualizaHUD(float fps) {
    const char* cam_str = Cam_jogo_travada ? "DEBUG (jogo travada)" : "JOGO ";
    std::cout << "\rCâm: [" << cam_str << "]  Culling: [" << (Frustum_culling_ativo ? "ON " : "OFF") << "] "
              << "Cena: " << std::setw(4) << Num_objetos << " | Desenhados: " << std::setw(4) << Objetos_desenhados
              << " | Culled: " << std::setw(4) << Objetos_culled << " | FPS: " << std::fixed << std::setprecision(1) << fps << "   " << std::flush;
}

// -----------------------------
// Loop de renderização
// -----------------------------

void inicializaRenderizacao() {
    glEnable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    std::cout << "\n--- Exemplo: Debug Visual do Frustum Culling ---" << std::endl;
    std::cout << "  T          — travar câmera de jogo e ativar câmera de debug" << std::endl;
    std::cout << "  C          — alternar frustum culling (culled = vermelho / tudo azul)" << std::endl;
    std::cout << "  +/-        — mais/menos objetos" << std::endl;
    std::cout << "  W/A/S/D    — mover câmera ativa" << std::endl;
    std::cout << "  ESC        — fechar\n" << std::endl;

    float t_ant = (float)glfwGetTime();
    _fps_timer = t_ant;

    while(!glfwWindowShouldClose(Window)) {
        float t_atual = (float)glfwGetTime();
        Tempo_entre_frames = t_atual - t_ant; t_ant = t_atual;
        
        glClearColor(0.15f, 0.15f, 0.2f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        glUseProgram(Shader_programm);
        especificaCamera();
        
        auto planos = extraiPlanosFrustum();
        atualizaFrustumWireframe();

        // Passo 1: Desenha todos os cubos
        // Azul  → dentro do frustum (visível para a câmera de jogo)
        // Vermelho semitransparente → fora do frustum (culled — "raio-x" do que seria descartado)
        glBindVertexArray(Vao_cubo);
        Objetos_desenhados = 0; Objetos_culled = 0;
        GLint cLoc = glGetUniformLocation(Shader_programm, "corobjeto");

        for(auto &pos : Objetos_posicoes) {
            bool in = estaNoFrustum(pos, Bounding_raio, planos);
            if(in) {
                glUniform4f(cLoc, 0.3f, 0.6f, 1.0f, 1.0f); Objetos_desenhados++;
            } else {
                Objetos_culled++;
                if(!Frustum_culling_ativo) { 
                    glUniform4f(cLoc, 0.3f, 0.6f, 1.0f, 1.0f); Objetos_desenhados++; 
                } else {
                    glUniform4f(cLoc, 1.0f, 0.15f, 0.15f, 0.35f);
                }
            }
            transformacaoGenerica(pos, glm::vec3(1.0f));
            glDrawArrays(GL_TRIANGLES, 0, 36);
        }

        // Passo 2: Desenha o wireframe do frustum
        if(Cam_jogo_travada) {
            glBindVertexArray(Vao_frustum);
            transformacaoGenerica(glm::vec3(0), glm::vec3(1));
            glUniform4f(cLoc, 1.0f, 0.9f, 0.0f, 1.0f);
            glLineWidth(2.0f); glDrawArrays(GL_LINES, 0, 24);
        }

        glfwPollEvents(); glfwSwapBuffers(Window); trataTeclado();
        
        _fps_frames++; _fps_acumulado += (Tempo_entre_frames > 0 ? 1.0f/Tempo_entre_frames : 0);
        if(t_atual - _fps_timer >= 1.0) {
            atualizaHUD(_fps_acumulado/_fps_frames);
            _fps_timer = t_atual; _fps_frames = 0; _fps_acumulado = 0;
        }
    }
}

int main() {
    inicializaOpenGL(); inicializaShaders(); inicializaCubo();
    inicializaFrustumWireframe(); geraObjetos(); inicializaRenderizacao();
    return 0;
}