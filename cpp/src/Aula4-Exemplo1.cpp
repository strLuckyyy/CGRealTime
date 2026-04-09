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

#include <iostream>
#include <vector>
#include <string>
#include <cmath>

#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

using namespace std;

GLFWwindow* Window = nullptr;

// -----------------------------
// NOVO: 2 programas (simples e pesado)
// -----------------------------
GLuint Shader_programm_simple = 0;
GLuint Shader_programm_heavy = 0;
GLuint Shader_programm = 0;

// -----------------------------
// NOVO: 3 malhas (LOD A/B/C)
// -----------------------------
struct Mesh
{
    GLuint vao = 0;
    GLuint vbo = 0;
    int vertexCount = 0;
    int triangleCount = 0;
};

vector<Mesh> Meshes;
int LOD_index = 0;

// -----------------------------
// NOVO: estados do experimento
// -----------------------------
bool Wireframe_enabled = false;
bool Heavy_shader_enabled = false;
bool Overdraw_heatmap_enabled = false;

int WIDTH = 800;
int HEIGHT = 600;

float Tempo_entre_frames = 0.0f;

// -----------------------------
// Câmera (base)
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
// NOVO: edge de teclas
// -----------------------------
static bool PrevKeyState[1024] = { false };

// -----------------------------
// HUD no título (1x por segundo)
// -----------------------------
static double HudAccum = 0.0;
static int HudFrames = 0;

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

    float xoffset = (float)(xpos - lastX);
    float yoffset = (float)(lastY - ypos);
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

bool keyPressedOnce(int key)
{
    if (key < 0 || key >= 1024) return false;

    bool current = glfwGetKey(Window, key) == GLFW_PRESS;
    bool previous = PrevKeyState[key];
    PrevKeyState[key] = current;

    return current && !previous;
}

void inicializaOpenGL()
{
    glfwInit();

    Window = glfwCreateWindow(WIDTH, HEIGHT, "Aula 4 - Exemplo 1 (Triangulos x Custo)", nullptr, nullptr);
    glfwMakeContextCurrent(Window);

    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);

    glfwSetFramebufferSizeCallback(Window, redimensionaCallback);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetKeyCallback(Window, key_callback);
    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);

    cout << "Placa de video: " << glGetString(GL_RENDERER) << endl;
    cout << "Versao do OpenGL: " << glGetString(GL_VERSION) << endl;
}

// -----------------------------
// Shaders (mantém o contrato do base)
// -----------------------------
GLuint compilaShader(const char* source, GLenum type)
{
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);

    GLint ok = 0;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &ok);
    if (!ok)
    {
        char log[2048];
        glGetShaderInfoLog(shader, 2048, nullptr, log);
        cerr << "Erro compilando shader: " << log << endl;
    }

    return shader;
}

GLuint criaProgram(const char* vsSrc, const char* fsSrc)
{
    GLuint vs = compilaShader(vsSrc, GL_VERTEX_SHADER);
    GLuint fs = compilaShader(fsSrc, GL_FRAGMENT_SHADER);

    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs);
    glAttachShader(prog, fs);
    glLinkProgram(prog);

    GLint ok = 0;
    glGetProgramiv(prog, GL_LINK_STATUS, &ok);
    if (!ok)
    {
        char log[2048];
        glGetProgramInfoLog(prog, 2048, nullptr, log);
        cerr << "Erro linkando program: " << log << endl;
    }

    glDeleteShader(vs);
    glDeleteShader(fs);

    return prog;
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

    const char* fragment_simple = R"(
        #version 450
        out vec4 frag_colour;
        uniform vec4 corobjeto;

        void main() {
            frag_colour = corobjeto;
        }
    )";

    // NOVO: pesado (simula gargalo de fragmento)
    const char* fragment_heavy = R"(
        #version 450
        out vec4 frag_colour;
        uniform vec4 corobjeto;

        void main() {
            vec2 p = gl_FragCoord.xy * 0.002;
            float acc = 0.0;

            for (int i = 0; i < 80; ++i) {
                p = vec2(
                    sin(p.x * 1.7 + p.y * 1.3 + float(i) * 0.02),
                    cos(p.y * 1.5 - p.x * 1.1 + float(i) * 0.03)
                );
                acc += p.x * p.y;
            }

            float m = clamp(abs(acc) * 0.02, 0.0, 1.0);
            frag_colour = mix(corobjeto, vec4(0.2, 0.9, 0.3, 1.0), m);
        }
    )";

    Shader_programm_simple = criaProgram(vertex_shader, fragment_simple);
    Shader_programm_heavy  = criaProgram(vertex_shader, fragment_heavy);
    Shader_programm = Shader_programm_simple;
}

// -----------------------------
// Transformação de modelo (base)
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
// Câmera (base)
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
// Cor (base)
// -----------------------------
void defineCor(float r,float g,float b,float a)
{
    GLuint loc = glGetUniformLocation(Shader_programm, "corobjeto");
    glUniform4f(loc,r,g,b,a);
}

// -----------------------------
// NOVO: esfera triangulada (posições) e criação de Mesh
// triângulos ~= 2 * stacks * slices
// -----------------------------
vector<float> geraEsferaTriangulada(float radius, int stacks, int slices)
{
    vector<float> verts;
    verts.reserve((size_t)stacks * (size_t)slices * 6ull * 3ull);

    for (int i = 0; i < stacks; ++i)
    {
        float phi0 = (float)M_PI * ((float)i / (float)stacks);
        float phi1 = (float)M_PI * ((float)(i + 1) / (float)stacks);

        for (int j = 0; j < slices; ++j)
        {
            float theta0 = 2.0f * (float)M_PI * ((float)j / (float)slices);
            float theta1 = 2.0f * (float)M_PI * ((float)(j + 1) / (float)slices);

            auto pushVec3 = [&](float x, float y, float z) {
                verts.push_back(x); verts.push_back(y); verts.push_back(z);
            };

            auto P = [&](float phi, float theta) -> glm::vec3 {
                return glm::vec3(
                    radius * sin(phi) * cos(theta),
                    radius * cos(phi),
                    radius * sin(phi) * sin(theta)
                );
            };

            glm::vec3 p00 = P(phi0, theta0);
            glm::vec3 p10 = P(phi1, theta0);
            glm::vec3 p01 = P(phi0, theta1);
            glm::vec3 p11 = P(phi1, theta1);

            // 2 triângulos
            pushVec3(p00.x, p00.y, p00.z);
            pushVec3(p10.x, p10.y, p10.z);
            pushVec3(p11.x, p11.y, p11.z);

            pushVec3(p00.x, p00.y, p00.z);
            pushVec3(p11.x, p11.y, p11.z);
            pushVec3(p01.x, p01.y, p01.z);
        }
    }

    return verts;
}

Mesh criaMeshPosicao(const vector<float>& points)
{
    Mesh m;

    glGenVertexArrays(1, &m.vao);
    glGenBuffers(1, &m.vbo);

    glBindVertexArray(m.vao);
    glBindBuffer(GL_ARRAY_BUFFER, m.vbo);
    glBufferData(GL_ARRAY_BUFFER, points.size() * sizeof(float), points.data(), GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, (void*)0);
    glEnableVertexAttribArray(0);

    glBindVertexArray(0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);

    m.vertexCount = (int)(points.size() / 3);
    m.triangleCount = m.vertexCount / 3;

    return m;
}

void inicializaMalhasLOD()
{
    struct Conf { string name; int stacks; int slices; };
    vector<Conf> cfgs = {
        { "LOD A", 50, 50 },
        { "LOD B", 158, 158 },
        { "LOD C", 500, 500 }
    };

    for (auto& c : cfgs)
    {
        auto pts = geraEsferaTriangulada(0.75f, c.stacks, c.slices);
        Mesh m = criaMeshPosicao(pts);
        Meshes.push_back(m);

        cout << c.name << ": stacks=" << c.stacks
             << ", slices=" << c.slices
             << ", tris=" << m.triangleCount << endl;
    }
}

// -----------------------------
// Entrada de teclado (base + toggles)
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

    // NOVO: toggles por edge
    if (keyPressedOnce(GLFW_KEY_1))
        LOD_index = (LOD_index + 1) % 3;

    if (keyPressedOnce(GLFW_KEY_2))
        Wireframe_enabled = !Wireframe_enabled;

    if (keyPressedOnce(GLFW_KEY_4))
    {
        Heavy_shader_enabled = !Heavy_shader_enabled;
        Shader_programm = Heavy_shader_enabled ? Shader_programm_heavy : Shader_programm_simple;
    }

    if (keyPressedOnce(GLFW_KEY_5))
        Overdraw_heatmap_enabled = !Overdraw_heatmap_enabled;
}

// -----------------------------
// NOVO: estados (wireframe + overdraw)
// -----------------------------
void aplicaEstadosDeRender()
{
    if (Wireframe_enabled)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
    else
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);

    if (Overdraw_heatmap_enabled)
    {
        glEnable(GL_BLEND);
        glBlendFunc(GL_ONE, GL_ONE);
        glDepthMask(GL_FALSE);
    }
    else
    {
        glDisable(GL_BLEND);
        glDepthMask(GL_TRUE);
    }
}

// -----------------------------
// HUD no título (1x por segundo)
// -----------------------------
void atualizaHud(double dt)
{
    HudAccum += dt;
    HudFrames += 1;

    if (HudAccum >= 1.0)
    {
        double fps = (double)HudFrames / HudAccum;
        HudAccum = 0.0;
        HudFrames = 0;

        int tris = Meshes[LOD_index].triangleCount;
        string sh = Heavy_shader_enabled ? "HEAVY" : "SIMPLE";
        string wf = Wireframe_enabled ? "ON" : "OFF";
        string od = Overdraw_heatmap_enabled ? "ON" : "OFF";

        string title =
            "Aula 4 - Ex1 | LOD=" + to_string(LOD_index) +
            " tris=" + to_string(tris) +
            " | FPS=" + to_string((int)(fps + 0.5)) +
            " | WF=" + wf + " SH=" + sh + " OD=" + od;

        glfwSetWindowTitle(Window, title.c_str());
    }
}

// -----------------------------
// Renderização (base + LOD)
// -----------------------------
void inicializaRenderizacao()
{
    float tempo_anterior = (float)glfwGetTime();

    glEnable(GL_DEPTH_TEST);

    while(!glfwWindowShouldClose(Window))
    {
        float tempo_atual = (float)glfwGetTime();
        Tempo_entre_frames = tempo_atual - tempo_anterior;
        tempo_anterior = tempo_atual;

        glViewport(0, 0, WIDTH, HEIGHT);

        glClearColor(0.2f,0.3f,0.3f,1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        aplicaEstadosDeRender();

        glUseProgram(Shader_programm);
        inicializaCamera();

        Mesh& m = Meshes[LOD_index];
        glBindVertexArray(m.vao);

        if (Overdraw_heatmap_enabled)
            defineCor(0.03f, 0.03f, 0.06f, 1.0f);
        else
            defineCor(1.0f,0.6f,0.2f,1.0f);

        transformacaoGenerica(0,0,0,1,1,1,0,0,0);
        glDrawArrays(GL_TRIANGLES,0,m.vertexCount);

        glfwSwapBuffers(Window);
        glfwPollEvents();
        trataTeclado();

        atualizaHud((double)Tempo_entre_frames);
    }

    glfwTerminate();
}

int main()
{
    inicializaOpenGL();
    inicializaMalhasLOD();
    inicializaShaders();
    inicializaRenderizacao();
    return 0;
}