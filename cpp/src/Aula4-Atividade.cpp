
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

// General Configurations
GLFWwindow *Window = nullptr;
int WIDTH = 800;
int HEIGHT = 600;
float Time_between_frames = 0.0f;

// Shader Program
GLuint Shader_programm = 0;

// Camera Configurations
float Cam_speed = 10.0f;
float Cam_yaw_speed = 30.0f;
glm::vec3 Cam_pos(0.0f, 0.0f, 2.0f);
float Cam_yaw = 0.0f;
float Cam_pitch = 0.0f;

double lastX = WIDTH / 2.0;
double lastY = HEIGHT / 2.0;
bool first_mouse = true;

// Mesh Structure
struct Mesh
{
	GLuint vao = 0;
	GLuint vbo = 0;
	GLuint ebo = 0;

	int indices_count = 0;
	int rad_segments = 3;
	int height_segments = 1;

	bool show_cilinder = true;
};

float h = 2.0f;
float r = 1.0f;

Mesh mesh1, mesh2;

// Modes
static bool Last_wireframe_state = false;
static bool Wireframe_enabled = false;

// Input CD
static bool PrevKeyState[1024] = {false};

// HUD no título (1x por segundo)
static double HudAccum = 0.0;
static int HudFrames = 0;

void resize_callback(GLFWwindow *window, int w, int h)
{
	WIDTH = w;
	HEIGHT = h;
	glViewport(0, 0, w, h);
}

void mouse_callback(GLFWwindow *window, double xpos, double ypos)
{
	if (first_mouse)
	{
		lastX = xpos;
		lastY = ypos;
		first_mouse = false;
	}

	float xoffset = (float)(xpos - lastX);
	float yoffset = (float)(lastY - ypos);
	lastX = xpos;
	lastY = ypos;

	float sensibility = 0.1f;
	xoffset *= sensibility;
	yoffset *= sensibility;

	Cam_yaw += xoffset;
	Cam_pitch += yoffset;

	Cam_pitch = glm::clamp(Cam_pitch, -89.0f, 89.0f);
}

void key_callback(GLFWwindow *window, int key, int scancode, int action, int mods)
{
}

bool key_pressed_once(int key)
{
	if (key < 0 || key >= 1024)
		return false;

	bool current = glfwGetKey(Window, key) == GLFW_PRESS;
	bool previous = PrevKeyState[key];
	PrevKeyState[key] = current;

	return current && !previous;
}

void keyboard_handle()
{
	float speed = Cam_speed * Time_between_frames;

	glm::vec3 front;
	front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
	front.y = sin(glm::radians(Cam_pitch));
	front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
	front = glm::normalize(front);

	glm::vec3 right = glm::normalize(glm::cross(front, glm::vec3(0, 1, 0)));

	if (glfwGetKey(Window, GLFW_KEY_W) == GLFW_PRESS)
		Cam_pos += front * speed;
	if (glfwGetKey(Window, GLFW_KEY_S) == GLFW_PRESS)
		Cam_pos -= front * speed;
	if (glfwGetKey(Window, GLFW_KEY_A) == GLFW_PRESS)
		Cam_pos -= right * speed;
	if (glfwGetKey(Window, GLFW_KEY_D) == GLFW_PRESS)
		Cam_pos += right * speed;

	if (glfwGetKey(Window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
		glfwSetWindowShouldClose(Window, true);

	if (key_pressed_once(GLFW_KEY_SPACE))
		Wireframe_enabled = !Wireframe_enabled;

	if (key_pressed_once(GLFW_KEY_1))
	{
		mesh1.show_cilinder = !mesh1.show_cilinder;
	}

	if (key_pressed_once(GLFW_KEY_2))
	{
		mesh2.show_cilinder = !mesh2.show_cilinder;
	}
}

vector<float> build_cilinder(float segments_rad, float segments_height)
{
	vector<float> vertices;

	for (int i = 0; i <= segments_height; ++i)
	{
		float y = -h / 2.f + i * (h / segments_height);
		for (int j = 0; j <= segments_rad; j++)
		{
			float theta = j * (2.f * (float)M_PI / segments_rad);
			float x = r * glm::cos(theta);
			float z = r * glm::sin(theta);

			float nx = glm::cos(theta);
			float ny = 0.0f;
			float nz = glm::sin(theta);

			vertices.push_back(x);
			vertices.push_back(y);
			vertices.push_back(z);
			vertices.push_back(nx);
			vertices.push_back(ny);
			vertices.push_back(nz);
		}
	}

	return vertices;
}

vector<unsigned int> connect_vertices(float segments_rad, float segments_height)
{
	vector<unsigned int> ebo;
	int stride = (int)segments_rad + 1;

	for (int i = 0; i < (int)segments_height; ++i)
	{
		for (int j = 0; j < (int)segments_rad; j++)
		{
			unsigned int p1 = i * stride + j;
			unsigned int p2 = (i + 1) * stride + j;
			unsigned int p3 = i * stride + (j + 1);
			unsigned int p4 = (i + 1) * stride + (j + 1);

			ebo.push_back(p1);
			ebo.push_back(p2);
			ebo.push_back(p3);

			ebo.push_back(p2);
			ebo.push_back(p4);
			ebo.push_back(p3);
		}
	}

	return ebo;
}

void cilinder_init()
{
	// Cilinder 1
	mesh1.rad_segments = 35;
	mesh1.height_segments = 5;

	vector<float> vertices = build_cilinder(mesh1.rad_segments, mesh1.height_segments);
	vector<unsigned int> indices = connect_vertices(mesh1.rad_segments, mesh1.height_segments);
	mesh1.indices_count = (int)indices.size();

	glGenVertexArrays(1, &mesh1.vao);
	glGenBuffers(1, &mesh1.vbo);
	glGenBuffers(1, &mesh1.ebo);

	glBindVertexArray(mesh1.vao);
	glBindBuffer(GL_ARRAY_BUFFER, mesh1.vbo);
	glBufferData(GL_ARRAY_BUFFER, vertices.size() * sizeof(float), vertices.data(), GL_STATIC_DRAW);

	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh1.ebo);
	glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.size() * sizeof(unsigned int), indices.data(), GL_STATIC_DRAW);

	glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void *)0);
	glEnableVertexAttribArray(0);
	glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void *)(3 * sizeof(float)));
	glEnableVertexAttribArray(1);

	vertices.clear();
	indices.clear();

	// Cilinder 2
	mesh2.rad_segments = 5;
	mesh2.height_segments = 35;

	vertices = build_cilinder(mesh2.rad_segments, mesh2.height_segments);
	indices = connect_vertices(mesh2.rad_segments, mesh2.height_segments);
	mesh2.indices_count = (int)indices.size();

	glGenVertexArrays(1, &mesh2.vao);
	glGenBuffers(1, &mesh2.vbo);
	glGenBuffers(1, &mesh2.ebo);

	glBindVertexArray(mesh2.vao);
	glBindBuffer(GL_ARRAY_BUFFER, mesh2.vbo);
	glBufferData(GL_ARRAY_BUFFER, vertices.size() * sizeof(float), vertices.data(), GL_STATIC_DRAW);

	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh2.ebo);
	glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.size() * sizeof(unsigned int), indices.data(), GL_STATIC_DRAW);

	glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void *)0);
	glEnableVertexAttribArray(0);
	glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void *)(3 * sizeof(float)));
	glEnableVertexAttribArray(1);
}

void openGL_init()
{
	mesh1.rad_segments = 35;
	mesh1.height_segments = 5;
	mesh2.rad_segments = 5;
	mesh2.height_segments = 35;

	glfwInit();

	Window = glfwCreateWindow(WIDTH, HEIGHT, "Aula 4 - Atividade", nullptr, nullptr);
	glfwMakeContextCurrent(Window);

	gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);

	glViewport(0, 0, WIDTH, HEIGHT);
	glEnable(GL_DEPTH_TEST);

	glfwSetFramebufferSizeCallback(Window, resize_callback);
	glfwSetCursorPosCallback(Window, mouse_callback);
	glfwSetKeyCallback(Window, key_callback);
	glfwSetInputMode(Window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
}

GLuint shaders_compiler(const char *source, GLenum type)
{
	GLuint shader = glCreateShader(type);
	glShaderSource(shader, 1, &source, nullptr);
	glCompileShader(shader);

	GLint success = 0;
	glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
	if (!success)
	{
		char infoLog[512];
		glGetShaderInfoLog(shader, 512, nullptr, infoLog);
		cerr << "ERROR::SHADER_COMPILATION_ERROR of type: " << type << "\n"
			 << infoLog << endl;
	}

	return shader;
}

GLuint program_create(const char *vertexSource, const char *fragmentSource)
{
	GLuint vertexShader = shaders_compiler(vertexSource, GL_VERTEX_SHADER);
	GLuint fragmentShader = shaders_compiler(fragmentSource, GL_FRAGMENT_SHADER);

	GLuint shaderProgram = glCreateProgram();
	glAttachShader(shaderProgram, vertexShader);
	glAttachShader(shaderProgram, fragmentShader);
	glLinkProgram(shaderProgram);

	GLint success = 0;
	glGetProgramiv(shaderProgram, GL_LINK_STATUS, &success);
	if (!success)
	{
		char infoLog[512];
		glGetProgramInfoLog(shaderProgram, 512, nullptr, infoLog);
		cerr << "ERROR::PROGRAM_LINKING_ERROR\n"
			 << infoLog << endl;
	}

	glDeleteShader(vertexShader);
	glDeleteShader(fragmentShader);

	return shaderProgram;
}

void shaders_init()
{
	const char *vertex_shader = R"(
        #version 400
        layout(location = 0) in vec3 vertex_posicao;
        layout(location = 1) in vec3 vertex_normal;
        
        uniform mat4 transform, view, proj;
        out vec3 world_normal;

        void main () {
            gl_Position  = proj * view * transform * vec4(vertex_posicao, 1.0);
            
			mat3 normal_matrix = mat3(transpose(inverse(view * transform)));
            world_normal = normal_matrix * vertex_normal;
        }
    )";

	const char *fragment_simple = R"(
        #version 400
        in  vec3 world_normal;
        out vec4 frag_colour;
        uniform vec4 objectcolor;
        uniform vec3 light_dir = normalize(vec3(1.0, 1.0, 1.0));  

        void main () {            
            vec3  normal     = normalize(world_normal);
            float diffuse    = max(dot(normal, light_dir), 0.0);
            float ambient    = 0.2;
            float intensity  = diffuse + ambient;
            frag_colour      = vec4(objectcolor.rgb * intensity, objectcolor.a);
        }
    )";

	Shader_programm = program_create(vertex_shader, fragment_simple);
}

void generic_transformation(float Tx, float Ty, float Tz,
							float Sx = 1.0f, float Sy = 1.0f, float Sz = 1.0f,
							float Rx = 0.0f, float Ry = 0.0f, float Rz = 0.0f)
{
	glm::mat4 transform(1.0f);

	transform = glm::translate(transform, glm::vec3(Tx, Ty, Tz));
	transform = glm::rotate(transform, glm::radians(Rz), glm::vec3(0, 0, 1));
	transform = glm::rotate(transform, glm::radians(Ry), glm::vec3(0, 1, 0));
	transform = glm::rotate(transform, glm::radians(Rx), glm::vec3(1, 0, 0));
	transform = glm::scale(transform, glm::vec3(Sx, Sy, Sz));

	GLuint loc = glGetUniformLocation(Shader_programm, "transform");
	glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(transform));
}

void specify_view_matrix()
{
	glm::vec3 front;
	front.x = cos(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
	front.y = sin(glm::radians(Cam_pitch));
	front.z = sin(glm::radians(Cam_yaw)) * cos(glm::radians(Cam_pitch));
	front = glm::normalize(front);

	glm::mat4 view = glm::lookAt(Cam_pos, Cam_pos + front, glm::vec3(0, 1, 0));

	GLuint loc = glGetUniformLocation(Shader_programm, "view");
	glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(view));
}

void specify_projection_matrix()
{
	glm::mat4 proj = glm::perspective(glm::radians(67.0f),
									  (float)WIDTH / HEIGHT,
									  0.1f, 100.0f);

	GLuint loc = glGetUniformLocation(Shader_programm, "proj");
	glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(proj));
}

void camera_init()
{
	specify_view_matrix();
	specify_projection_matrix();
}

void set_color(float r, float g, float b, float a)
{
	GLuint loc = glGetUniformLocation(Shader_programm, "objectcolor");
	glUniform4f(loc, r, g, b, a);
}

void update_hud(double dt)
{
	HudAccum += dt;
	HudFrames += 1;

	if (HudAccum >= 1.0)
	{
		double fps = (double)HudFrames / HudAccum;
		HudAccum = 0.0;
		HudFrames = 0;

		string wf = Wireframe_enabled ? "ON" : "OFF";
		string sh = mesh1.show_cilinder ? "ON" : "OFF";
		string sh2 = mesh2.show_cilinder ? "ON" : "OFF";

		string title =
			"Aula 4 - Atividade | FPS=" + to_string((int)(fps + 0.5)) +
			" | WF=" + wf +
			" | SH1=" + sh +
			" | SH2=" + sh2;

		glfwSetWindowTitle(Window, title.c_str());
	}
}

void render_init()
{
	float Last_time = (float)glfwGetTime();

	while (!glfwWindowShouldClose(Window))
	{
		float Current_time = (float)glfwGetTime();
		Time_between_frames = Current_time - Last_time;
		Last_time = Current_time;

		glViewport(0, 0, WIDTH, HEIGHT);
		glClearColor(0.2f, 0.3f, 0.3f, 1.0f);
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

		keyboard_handle();
		update_hud(Time_between_frames);

		glUseProgram(Shader_programm);
		camera_init();

		if (Wireframe_enabled != Last_wireframe_state)
		{
			Last_wireframe_state = Wireframe_enabled;
			if (Wireframe_enabled)
				glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
			else
				glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
		}

		if (mesh1.show_cilinder)
		{
			set_color(1.0f, 0.0f, 0.0f, 1.0f);
			glBindVertexArray(mesh1.vao);
			generic_transformation(0.f, 0.0f, 0.0f);

			glDrawElements(GL_TRIANGLES, mesh1.indices_count, GL_UNSIGNED_INT, nullptr);
		}

		if (mesh2.show_cilinder)
		{
			set_color(0.0f, 0.0f, 1.0f, 1.0f);
			glBindVertexArray(mesh2.vao);

			generic_transformation(3.0f, 0.0f, 0.0f);

			glDrawElements(GL_TRIANGLES, mesh2.indices_count, GL_UNSIGNED_INT, nullptr);
		}

		glfwSwapBuffers(Window);
		glfwPollEvents();
	}
	glfwTerminate();
}

int main()
{
	openGL_init();
	shaders_init();
	cilinder_init();
	render_init();

	return 0;
}