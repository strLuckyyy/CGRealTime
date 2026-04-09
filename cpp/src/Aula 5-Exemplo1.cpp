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
#include <algorithm>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Backface Culling - exemplo para a disciplina de Computação Gráfica em Tempo Real
//
// Este exemplo demonstra o conceito de Backface Culling:
// o descarte automático das faces traseiras de objetos opacos antes da rasterização.
//
// Conceitos demonstrados:
// - Winding Order (CCW): a ordem anti-horária dos vértices define a "frente" do polígono
// - Backface Culling: faces cujo winding aparece horário na tela são descartadas pela GPU
// - Ganho de ~50%: em qualquer objeto fechado e opaco, metade das faces está sempre de costas
// - Frontface Culling: curiosidade didática - descarta a frente e exibe o interior do objeto
//
// Controles:
//   W/A/S/D     - mover câmera (FPS)
//   Mouse       - girar câmera
//   C           - alternar modo de culling (SEM / BACKFACE / FRONTFACE)
//   W (tecla)   - wireframe on/off (tecla F)
//   ESC         - fechar
//
// HUD no terminal (a cada ~1 segundo):
//   Modo de culling ativo, faces descartadas (estimativa), FPS médio

GLFWwindow* Window = nullptr;
GLuint Shader_programm = 0;
GLuint Vao_esfera = 0;   // usamos uma esfera de alta resolução para o efeito ser visível
int WIDTH = 800;
int HEIGHT = 600;

float Tempo_entre_frames = 0.0f;  // variavel utilizada para movimentar a camera

// Variáveis referentes a câmera virtual e sua projeção

float Cam_speed = 10.0f;  // velocidade da camera, 10 unidades por segundo
glm::vec3 Cam_pos = glm::vec3(0.0f, 0.0f, 3.0f);  // posicao inicial da câmera
float Cam_yaw = -90.0f;  // olhando para a origem
float Cam_pitch = 0.0f;    // controle vertical
double lastX = 400.0, lastY = 300.0;
bool primeiro_mouse = true;

// -----------------------------
// Estado da demonstração
// -----------------------------

// Modos de culling:
//   0 -> SEM culling    (GL_FRONT_AND_BACK desativado - todas as faces renderizadas)
//   1 -> BACKFACE       (GL_BACK  - faces traseiras descartadas, ganho de ~50%)
//   2 -> FRONTFACE      (GL_FRONT - apenas interior visível, curiosidade didática)
int Modo_culling = 0;

// Wireframe
bool Wireframe = false;

// Número de triângulos gerados na esfera (preenchido em inicializaEsfera)
int Num_triangulos = 0;

// Acumuladores de FPS para o HUD
float _fps_acumulado = 0.0f;
int _fps_frames = 0;
double _fps_timer = 0.0;

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

    Cam_yaw += (float)xoffset;
    Cam_pitch += (float)yoffset;

    Cam_pitch = std::max(-89.0f, std::min(89.0f, Cam_pitch));
}

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mode) {
    if (action != GLFW_PRESS)
        return;

    // C - cicla entre os três modos de culling
    if (key == GLFW_KEY_C) {
        Modo_culling = (Modo_culling + 1) % 3;
        const char* nomes[] = { "SEM culling (todas as faces)", "BACKFACE culling (~50% descartado)", "FRONTFACE culling (interior visível)" };
        std::cout << "\n[CULLING] " << nomes[Modo_culling] << std::endl;
    }

    // F - alterna wireframe
    if (key == GLFW_KEY_F) {
        Wireframe = !Wireframe;
        glPolygonMode(GL_FRONT_AND_BACK, Wireframe ? GL_LINE : GL_FILL);
        std::cout << "\n[WIRE] Wireframe " << (Wireframe ? "ON" : "OFF") << std::endl;
    }
}

// -----------------------------
// Inicialização do OpenGL
// -----------------------------

void inicializaOpenGL() {
    // Inicializa GLFW
    if (!glfwInit()) exit(EXIT_FAILURE);

    // Criação de uma janela
    Window = glfwCreateWindow(WIDTH, HEIGHT, "Exemplo Backface Culling - CG em Tempo Real", NULL, NULL);
    if (!Window) {
        glfwTerminate();
        exit(EXIT_FAILURE);
    }

    glfwSetWindowSizeCallback(Window, redimensionaCallback);
    glfwMakeContextCurrent(Window);

    // Inicializa GLAD para carregar os ponteiros das funções OpenGL
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
        std::cout << "Falha ao inicializar GLAD" << std::endl;
        exit(EXIT_FAILURE);
    }

    glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(Window, mouse_callback);
    glfwSetKeyCallback(Window, key_callback);

    std::cout << "Placa de vídeo: " << glGetString(GL_RENDERER) << std::endl;
    std::cout << "Versão do OpenGL: " << glGetString(GL_VERSION) << std::endl;
}

// -----------------------------
// Inicialização da geometria: esfera UV
// -----------------------------
// Usamos uma esfera de alta resolução (muitos triângulos) para que o impacto
// do culling seja visível tanto em wireframe quanto no FPS.
//
// A esfera é definida por uma grade UV de anéis (rings) e setores (sectors).
// Cada célula da grade gera 2 triângulos.
//
// IMPORTANTE sobre o Winding Order (CCW):
//   Os vértices de cada triângulo são listados em ordem ANTI-HORÁRIA quando vistos
//   de fora da esfera. Isso define a "frente" de cada face - o lado voltado para fora.
//   Quando a câmera vê uma face de trás, a projeção 2D inverte a ordem para HORÁRIA
//   (área negativa), e a GPU a descarta automaticamente com o culling ativado.

void inicializaEsfera(int rings = 48, int sectors = 64, float raio = 1.0f) {
    std::vector<float> pontos;

    for (int r = 0; r < rings; ++r) {
        for (int s = 0; s < sectors; ++s) {
            // Ângulos dos quatro cantos da célula (r, s)
            float theta0 = (float)M_PI * r / rings;
            float theta1 = (float)M_PI * (r + 1) / rings;
            float phi0 = 2.0f * (float)M_PI * s / sectors;
            float phi1 = 2.0f * (float)M_PI * (s + 1) / sectors;

            // Quatro vértices da célula esférica
            glm::vec3 v00(sin(theta0) * cos(phi0), cos(theta0), sin(theta0) * sin(phi0));
            glm::vec3 v01(sin(theta0) * cos(phi1), cos(theta0), sin(theta0) * sin(phi1));
            glm::vec3 v10(sin(theta1) * cos(phi0), cos(theta1), sin(theta1) * sin(phi0));
            glm::vec3 v11(sin(theta1) * cos(phi1), cos(theta1), sin(theta1) * sin(phi1));

            v00 *= raio; v01 *= raio; v10 *= raio; v11 *= raio;

            // Triângulo 1 - ordem CCW vista de fora da esfera
            pontos.push_back(v00.x); pontos.push_back(v00.y); pontos.push_back(v00.z);
            pontos.push_back(v10.x); pontos.push_back(v10.y); pontos.push_back(v10.z);
            pontos.push_back(v11.x); pontos.push_back(v11.y); pontos.push_back(v11.z);
            // Triângulo 2 - ordem CCW vista de fora da esfera
            pontos.push_back(v00.x); pontos.push_back(v00.y); pontos.push_back(v00.z);
            pontos.push_back(v11.x); pontos.push_back(v11.y); pontos.push_back(v11.z);
            // v01 deve manter o sentido CCW em relação a v00 e v11
            pontos.push_back(v01.x); pontos.push_back(v01.y); pontos.push_back(v01.z);
        }
    }

    Num_triangulos = (int)pontos.size() / 9; // 3 vértices * 3 coords = 9 floats por triângulo

    glGenVertexArrays(1, &Vao_esfera);
    glBindVertexArray(Vao_esfera);

    GLuint pvbo;
    glGenBuffers(1, &pvbo);
    glBindBuffer(GL_ARRAY_BUFFER, pvbo);
    glBufferData(GL_ARRAY_BUFFER, pontos.size() * sizeof(float), pontos.data(), GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, NULL);

    std::cout << "[ESFERA] " << Num_triangulos << " triângulos gerados (" << rings << " rings x " << sectors << " sectors)" << std::endl;
}

// -----------------------------
// Shaders
// -----------------------------
// Idênticos ao exemplo base.

void inicializaShaders() {
    // Especificação do Vertex Shader:
    const char* vertex_shader = R"(
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        //view - matriz da câmera recebida do C++
        //proj - matriz de projeção recebida do C++
        //transform - matriz de transformação geométrica do objeto recebida do C++
        uniform mat4 transform, view, proj;
        void main () {
            gl_Position = proj*view*transform*vec4(vertex_posicao, 1.0);
        }
    )";

    // Especificação do Fragment Shader:
    const char* fragment_shader = R"(
        #version 400
        out vec4 frag_colour;
        uniform vec4 corobjeto;
        void main () {
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

    glDeleteShader(vs);
    glDeleteShader(fs);
}

// -----------------------------
// Transformação de modelo
// -----------------------------

void transformacaoGenerica(float Tx, float Ty, float Tz, float Sx, float Sy, float Sz, float Rx, float Ry, float Rz) {
    glm::mat4 model = glm::mat4(1.0f);
    model = glm::translate(model, glm::vec3(Tx, Ty, Tz));
    model = glm::rotate(model, glm::radians(Rx), glm::vec3(1, 0, 0));
    model = glm::rotate(model, glm::radians(Ry), glm::vec3(0, 1, 0));
    model = glm::rotate(model, glm::radians(Rz), glm::vec3(0, 0, 1));
    model = glm::scale(model, glm::vec3(Sx, Sy, Sz));

    // E passamos a matriz para o Vertex Shader.
    GLint transformLoc = glGetUniformLocation(Shader_programm, "transform");
    glUniformMatrix4fv(transformLoc, 1, GL_FALSE, glm::value_ptr(model));
}

// -----------------------------
// Câmera (matriz de visualização)
// -----------------------------

void especificaMatrizVisualizacao() {
    /**
    Implementa um sistema de câmera no estilo FPS usando uma matriz lookAt manual.

    A ideia geral do lookAt é simular uma câmera no espaço 3D - ou seja, um ponto (posição da câmera)
    e uma direção (para onde ela está olhando). Em vez de mover a câmera diretamente,
    o que fazemos é aplicar a transformação inversa no mundo: deslocamos e rotacionamos
    tudo o que é desenhado, como se a câmera estivesse fixa na origem.

    Etapas principais:
      - A câmera tem posição (Cam_pos) e orientação (yaw/pitch):
        -> yaw controla a rotação horizontal (esquerda/direita),
        -> pitch controla a rotação vertical (cima/baixo).

      - A partir de yaw e pitch, calculamos o vetor 'front':
        ->é o vetor que aponta exatamente na direção para onde a câmera está olhando.
        ->Ele é normalizado para ter magnitude 1.

      - O vetor 'right' (ou 's') é obtido pelo produto vetorial entre 'front' e o eixo Y mundial (0,1,0):
        ->ele aponta para o lado direito da câmera e serve para calcular movimentos laterais (A/D).
        ->Esse vetor é sempre perpendicular ao 'front' e ao 'up' mundial.

      - O vetor 'up' (ou 'u') é recalculado como o produto vetorial entre 'right' e 'front':
        ->ele garante que o sistema de coordenadas da câmera forme uma base ortogonal
        (ou seja, os três vetores são perpendiculares entre si e normalizados).

    Montagem da matriz:
      - A matriz de visualização é formada colocando 'right', 'up' e '-front' nas três primeiras linhas:
            |  sx   sy   sz  -dot(s, Cam_pos) |
            |  ux   uy   uz  -dot(u, Cam_pos) |
            | -fx  -fy  -fz   dot(f, Cam_pos) |
            |   0    0    0         1         |
        Onde:
          s = right
          u = up
          f = front
        O termo -dot(...) representa a translação inversa da posição da câmera.

      - Essa matriz transforma o mundo para o referencial da câmera:
        ->o que está "na frente" da câmera é trazido para o eixo -Z,
        ->o "lado direito" para o +X e o "cima" para o +Y, como no sistema de visão padrão do OpenGL.

    Resultado:
      - O OpenGL renderiza como se a câmera estivesse sempre na origem (0,0,0),
        olhando para a direção (0,0,-1), e todo o resto do mundo se move ao redor dela.
    */
    glm::vec3 front;
    front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front.y = sin(glm::radians(Cam_pitch));
    front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    front = glm::normalize(front);

    glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + front, glm::vec3(0.0f, 1.0f, 0.0f));

    GLint viewLoc = glGetUniformLocation(Shader_programm, "view");
    glUniformMatrix4fv(viewLoc, 1, GL_FALSE, glm::value_ptr(view));
}

// -----------------------------
// Projeção
// -----------------------------

void especificaMatrizProjecao() {
    // Especificação da matriz de projeção perspectiva.
    float znear = 0.1f;    // recorte z-near
    float zfar = 100.0f;  // recorte z-far
    float fov = glm::radians(67.0f);  // campo de visão
    float aspecto = (float)WIDTH / (float)HEIGHT;   // aspecto

    glm::mat4 proj = glm::perspective(fov, aspecto, znear, zfar);

    GLint projLoc = glGetUniformLocation(Shader_programm, "proj");
    glUniformMatrix4fv(projLoc, 1, GL_FALSE, glm::value_ptr(proj));
}

void inicializaCamera() {
    especificaMatrizVisualizacao();  // posição da câmera e orientação da câmera (rotação)
    especificaMatrizProjecao();       // perspectiva ou paralela
}

// -----------------------------
// Entrada de teclado
// -----------------------------

void trataTeclado() {
    /**
    Movimenta a câmera no espaço 3D conforme teclas WASD.
    A direção do movimento segue o vetor 'front' (para onde o jogador está olhando),
    incluindo a inclinação vertical (pitch), assim o movimento é fiel ao olhar.
    */
    float velocidade = Cam_speed * Tempo_entre_frames;

    glm::vec3 frente;
    frente.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente.y = sin(glm::radians(Cam_pitch));
    frente.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
    frente = glm::normalize(frente);

    glm::vec3 direita = glm::normalize(glm::cross(frente, glm::vec3(0.0f, 1.0f, 0.0f)));

    // W/S: movem para frente/trás considerando o vetor de direção atual
    if (glfwGetKey(Window, GLFW_KEY_W) == GLFW_PRESS)
        Cam_pos += frente * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_S) == GLFW_PRESS)
        Cam_pos -= frente * velocidade;

    // A/D: movem lateralmente em relação à direção da câmera
    if (glfwGetKey(Window, GLFW_KEY_A) == GLFW_PRESS)
        Cam_pos -= direita * velocidade;
    if (glfwGetKey(Window, GLFW_KEY_D) == GLFW_PRESS)
        Cam_pos += direita * velocidade;

    if (glfwGetKey(Window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        glfwSetWindowShouldClose(Window, true);
}

// -----------------------------
// Definição de cor
// -----------------------------

void defineCor(float r, float g, float b, float a) {
    // array de cores que vamos mandar pro shader
    // buscou a localização na memória de video da variável corobjeto
    GLint coresLoc = glGetUniformLocation(Shader_programm, "corobjeto");
    // passa os valores do vetor de cores aqui do C++ para o shader
    glUniform4f(coresLoc, r, g, b, a);
}

// -----------------------------
// Aplicação do modo de culling
// -----------------------------
// Ativa ou desativa o GL_CULL_FACE conforme o modo atual.
// O OpenGL descarta faces com winding horário (área 2D negativa) na tela.
//
// Modo 0 - SEM culling:
//   glDisable(GL_CULL_FACE) → todas as faces chegam ao rasterizador.
//
// Modo 1 - BACKFACE culling:
//   glEnable(GL_CULL_FACE) + glCullFace(GL_BACK) → faces traseiras descartadas.
//   Como ~50% da esfera está sempre de costas, metade dos triângulos é eliminada
//   antes mesmo de chegar ao Fragment Shader - ganho imediato de desempenho.
//
// Modo 2 - FRONTFACE culling:
//   glEnable(GL_CULL_FACE) + glCullFace(GL_FRONT) → faces frontais descartadas.
//   O interior da esfera fica visível. Útil para debugar winding order,
//   ou para renderizar o interior de ambientes fechados.

void aplicaMododeCulling() {
    if (Modo_culling == 0) {
        // Sem culling - renderiza frente e verso de cada face
        glDisable(GL_CULL_FACE);
    }
    else if (Modo_culling == 1) {
        // Backface culling - descarta faces traseiras (winding horário na tela)
        glEnable(GL_CULL_FACE);
        glCullFace(GL_BACK);
        // glFrontFace(GL_CCW) é o padrão do OpenGL - não precisa ser chamado explicitamente,
        // mas vale mencionar: CCW (Counter-Clockwise) = frente do polígono.
    }
    else if (Modo_culling == 2) {
        // Frontface culling - descarta faces frontais (curiosidade pedagógica)
        glEnable(GL_CULL_FACE);
        glCullFace(GL_FRONT);
    }
}

// -----------------------------
// HUD no terminal
// -----------------------------

void atualizaHUD(float fps) {
    const char* nomes[] = { "SEM culling       ", "BACKFACE culling  ", "FRONTFACE culling " };
    // Estimativa de faces descartadas:
    //   Modo 0: nenhuma descartada
    //   Modo 1: ~50% descartadas (metade traseira do objeto fechado)
    //   Modo 2: ~50% descartadas (metade frontal)
    const char* descartadas[] = { "~0%  ", "~50% ", "~50% " };

    std::cout << "\r[" << nomes[Modo_culling] << "]  "
        << "Triângulos totais: " << std::setw(5) << Num_triangulos << "  |  "
        << "Faces descartadas: " << descartadas[Modo_culling] << "  |  "
        << "FPS: " << std::fixed << std::setprecision(1) << std::setw(6) << fps << "   " << std::flush;
}

// -----------------------------
// Loop de renderização
// -----------------------------

void inicializaRenderizacao() {
    float tempo_anterior = (float)glfwGetTime();
    _fps_timer = tempo_anterior;

    // Ativação do teste de profundidade. Sem ele, o OpenGL não sabe que faces devem ficar na frente e que faces devem ficar atrás.
    glEnable(GL_DEPTH_TEST);
    // Ativa mistura de cores, para podermos usar transparência
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    std::cout << "\n--- Exemplo: Backface Culling ---" << std::endl;
    std::cout << "  C      - alternar modo de culling (SEM / BACKFACE / FRONTFACE)" << std::endl;
    std::cout << "  F      - wireframe on/off  (ative para ver os triângulos!)" << std::endl;
    std::cout << "  W/A/S/D + mouse - câmera FPS" << std::endl;
    std::cout << "  ESC    - fechar\n" << std::endl;
    std::cout << "  Dica: ative o wireframe (F) para ver os triângulos sumindo com o culling!" << std::endl;

    while (!glfwWindowShouldClose(Window)) {
        // calcula quantos segundos se passaram entre um frame e outro
        float tempo_frame_atual = (float)glfwGetTime();
        Tempo_entre_frames = tempo_frame_atual - tempo_anterior;
        tempo_anterior = tempo_frame_atual;

        glClearColor(0.15f, 0.15f, 0.2f, 1.0f);  // define a cor do fundo da tela
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);  // limpa o buffer de cores e de profundidade

        glUseProgram(Shader_programm);

        // Aplica o modo de culling escolhido pelo aluno antes de desenhar
        aplicaMododeCulling();

        inicializaCamera();

        glBindVertexArray(Vao_esfera);

        // Cor varia conforme o modo para facilitar a identificação visual:
        //   azul  → sem culling (tudo visível) → todos os triângulos chegam ao rasterizador, frente e verso de cada face. Em wireframe, a esfera parece uma bola sólida de arame.
        //   verde → backface (modo normal, ganho de desempenho) → faces com winding horário na tela são descartadas. Em wireframe, a metade traseira da esfera some instantaneamente - o aluno vê exatamente o "ganho de 50%" citado nos slides.
        //   laranja → frontface (interior visível) → descarta a frente, exibe o interior. Conecta com o slide do Winding Order - o aluno entende que a "frente" é uma convenção matemática, não uma propriedade física.
        if (Modo_culling == 0) {
            defineCor(0.3f, 0.6f, 1.0f, 1.0f);   // azul
        }
        else if (Modo_culling == 1) {
            defineCor(0.3f, 0.9f, 0.4f, 1.0f);   // verde
        }
        else {
            defineCor(1.0f, 0.6f, 0.2f, 1.0f);   // laranja
        }

        transformacaoGenerica(0, 0, 0, 1, 1, 1, 0, 0, 0);
        glDrawArrays(GL_TRIANGLES, 0, Num_triangulos * 3);

        glfwPollEvents();
        glfwSwapBuffers(Window);
        trataTeclado();

        // Acumula FPS para o HUD
        _fps_frames += 1;
        _fps_acumulado += (Tempo_entre_frames > 0) ? (1.0f / Tempo_entre_frames) : 0.0f;

        if (tempo_frame_atual - _fps_timer >= 1.0) {
            float fps_medio = _fps_acumulado / _fps_frames;
            atualizaHUD(fps_medio);
            _fps_acumulado = 0.0f;
            _fps_frames = 0;
            _fps_timer = tempo_frame_atual;
        }
    }

    glfwTerminate();
}

// Função principal
int main() {
    inicializaOpenGL();
    inicializaShaders();
    inicializaEsfera(48, 64);  // esfera de alta resolução: ~6144 triângulos
    inicializaRenderizacao();
    return 0;
}