# Exercício - Sistema Solar
# Simulação 3D com texturas, iluminação Blinn-Phong e movimentação em escala
#
# CONTROLES:
#   W / A / S / D       - Movimentação da câmera (modo livre)
#   Mouse               - Rotação da câmera (modo livre)
#   1–0                 - Foca a câmera no planeta correspondente
#   SPACE               - Retorna ao modo de câmera livre
#   ESC                 - Fecha a janela
#
#   --- Velocidade da simulação ---
#   L                   - Aumenta velocidade (+10×)
#   K                   - Diminui velocidade (-10×)
#   J                   - Velocidade padrão (reset)
#
#   --- Modo de foco (câmera orbital) ---
#   Mouse               - Orbita ao redor do planeta
#   Scroll do mouse     - Zoom in / out
#
#
#   DICA: Se quiser aumentar o tamanho dos planetas para melhor visualização, 
#	altere a variável `radius_scale`(linha 90) no início do código (ex: `radius_scale = 7.0`).
#
# DEPENDÊNCIAS: pip install PyOpenGL PyOpenGL_accelerate glfw Pillow numpy

import os
import ctypes
from pathlib import Path

import glfw
import numpy as np
from PIL import Image
from OpenGL.GL import *
import OpenGL.GL.shaders

# =============================================================================
# CONFIGURAÇÕES E CONSTANTES
# =============================================================================

WINDOW_TITLE  = "Sistema Solar"
WIDTH, HEIGHT = 1280, 720

TEXTURE_DIR   = Path(__file__).parent / "textures"

SPHERE_SLICES = 64
SPHERE_STACKS = 32
RING_SLICES   = 64

# Câmera livre
CAM_SPEED       = 15.0
CAM_SENSITIVITY = 0.1

# Câmera orbital (modo foco)
ORBITAL_SENSITIVITY = 0.3
ORBITAL_ZOOM_SPEED  = 0.1

# Simulação
DEFAULT_SIM_SPEED = 1.0
SIM_SPEED_STEP    = 10.0
SIM_SPEED_MIN     = 0.1

# Projeção
FOV_DEG = 60.0
Z_NEAR  = 0.1
Z_FAR   = 20_000.0

# Mapeamento tecla → nome do planeta
KEY_PLANET_MAP = {
	glfw.KEY_1: "Sol",
	glfw.KEY_2: "Mercurio",
	glfw.KEY_3: "Venus",
	glfw.KEY_4: "Terra",
	glfw.KEY_5: "Lua",
	glfw.KEY_6: "Marte",
	glfw.KEY_7: "Jupiter",
	glfw.KEY_8: "Saturno",
	glfw.KEY_9: "Urano",
	glfw.KEY_0: "Netuno",
}

# =============================================================================
# DADOS DOS CORPOS CELESTES
# =============================================================================

radius_scale = 1.0 # Pode mudar para visualizar melhor os planetas no sistema solar

RADIUS   = np.array([(13.927/radius_scale), 0.049,  0.121,   0.128, 0.035, 0.068, 1.430,  1.205,   0.511,   0.495,  (10000.0/radius_scale)]) * radius_scale # Raio relativo (para renderização)
DISTANCE = np.array([0.0,                   57.9,   108.2,   149.6, 8.384, 228.0, 778.5,  1432.0,  2867.0,  4515.0,  0.0                  ])                # Distância relativa do Sol (para renderização)
ROTATION = np.array([609.1,                 1407.6, -5832.5, 23.9,  655.7, 24.6,  9.9,    10.7,    -17.2,   16.1,    0.0                  ])                # Período de rotação em horas (negativo = rotação retrógrada)
ORB      = np.array([0.0,                   88.0,   224.7,   365.2, 27.3,  687.0, 4331.0, 10747.0, 30589.0, 59800.0, 0.0                  ])                # Período orbital em dias
TILT     = np.array([7.25,                  0.03,   177.4,   23.5,  6.7,   25.2,  3.1,    26.7,    97.8,    28.3,    0.0                  ])                # Inclinação do eixo de rotação em graus

CELESTIAL_BODIES = {
	"Sol":      {"r": RADIUS[0],  "d": DISTANCE[0],  "rot": ROTATION[0],  "orb": ORB[0],  "tilt": TILT[0],  "tex": "2k_sun.jpg"             },
	"Mercurio": {"r": RADIUS[1],  "d": DISTANCE[1],  "rot": ROTATION[1],  "orb": ORB[1],  "tilt": TILT[1],  "tex": "2k_mercury.jpg"         },
	"Venus":    {"r": RADIUS[2],  "d": DISTANCE[2],  "rot": ROTATION[2],  "orb": ORB[2],  "tilt": TILT[2],  "tex": "2k_venus_surface.jpg", "tex_clouds": "2k_venus_atmosphere.jpg"},
	"Terra":    {"r": RADIUS[3],  "d": DISTANCE[3],  "rot": ROTATION[3],  "orb": ORB[3],  "tilt": TILT[3],  "tex": "2k_earth_daymap.jpg", "tex_clouds": "2k_earth_clouds.jpg"},
	"Lua":      {"r": RADIUS[4],  "d": DISTANCE[4],  "rot": ROTATION[4],  "orb": ORB[4],  "tilt": TILT[4],  "tex": "2k_moon.jpg"            },
	"Marte":    {"r": RADIUS[5],  "d": DISTANCE[5],  "rot": ROTATION[5],  "orb": ORB[5],  "tilt": TILT[5],  "tex": "2k_mars.jpg"            },
	"Jupiter":  {"r": RADIUS[6],  "d": DISTANCE[6],  "rot": ROTATION[6],  "orb": ORB[6],  "tilt": TILT[6],  "tex": "2k_jupiter.jpg"         },
	"Saturno":  {"r": RADIUS[7],  "d": DISTANCE[7],  "rot": ROTATION[7],  "orb": ORB[7],  "tilt": TILT[7],  "tex": "2k_saturn.jpg"          },
	"Urano":    {"r": RADIUS[8],  "d": DISTANCE[8],  "rot": ROTATION[8],  "orb": ORB[8],  "tilt": TILT[8],  "tex": "2k_uranus.jpg"          },
	"Netuno":   {"r": RADIUS[9],  "d": DISTANCE[9],  "rot": ROTATION[9],  "orb": ORB[9],  "tilt": TILT[9],  "tex": "2k_neptune.jpg"         },
	"Skybox":   {"r": RADIUS[10], "d": DISTANCE[10], "rot": ROTATION[10], "orb": ORB[10], "tilt": TILT[10], "tex": "2k_stars_milky_way.jpg" },
}

RENDER_ORDER        = ["Skybox", "Sol", "Mercurio", "Venus", "Terra", "Lua", "Marte", "Jupiter", "Saturno", "Urano", "Netuno"]
EMISSIVE_BODIES     = {"Sol", "Skybox"}

# Propriedades de material por planeta para iluminação Blinn-Phong realista.
# spec_strength : intensidade do highlight especular  (0 = fosco, 1 = muito brilhante)
# shininess     : concentração do highlight           (baixo = espalhado, alto = pontual)
MATERIAL = {
	"Mercurio": (0.03, 6 ),
	"Venus":    (0.12, 24),
	"Terra":    (0.32, 26),
	"Lua":      (0.02, 4 ),
	"Marte":    (0.04, 8 ),
	"Jupiter":  (0.12, 20),
	"Saturno":  (0.10, 18),
	"Urano":    (0.18, 40),
	"Netuno":   (0.20, 48),
	"Sol":      (0.0,  1 ),
	"Skybox":   (0.0,  1 )
}

# =============================================================================
# SHADERS
# =============================================================================

VERTEX_SHADER_SPHERE = """
	#version 400
	layout(location = 0) in vec3 aPos;
	layout(location = 1) in vec3 aNormal;
	layout(location = 2) in vec2 aTex;

	uniform mat4 model;
	uniform mat4 view;
	uniform mat4 proj;

	out vec3 FragPos;
	out vec3 Normal;
	out vec2 UV;

	void main() {
		vec4 worldPos = model * vec4(aPos, 1.0);
		FragPos = worldPos.xyz;
		Normal = mat3(transpose(inverse(model))) * aNormal;
		UV = vec2(1.0 - aTex.x, aTex.y);
		gl_Position = proj * view * worldPos;
	}
"""

FRAGMENT_SHADER_SPHERE = """
	#version 400
	in vec3 FragPos;
	in vec3 Normal;
	in vec2 UV;

	out vec4 frag_color;

	uniform sampler2D tex_diffuse;
	uniform sampler2D tex_clouds;
	uniform bool      useClouds;
	uniform float     uCloudOffset;
	uniform float     uCloudAlpha;

	uniform vec3      lightPos;
	uniform vec3      viewPos;
	uniform bool      isEmissive;
	uniform float     uSpecStrength;
	uniform float     uShininess;

	void main() {
		vec4 texColor = texture(tex_diffuse, UV);

		if (useClouds) {
			vec2 cloudUV    = vec2(UV.x + uCloudOffset, UV.y);
			vec4 cloudColor = texture(tex_clouds, cloudUV);
			float cloudMask = max(cloudColor.r, max(cloudColor.g, cloudColor.b));;
			
			texColor.rgb = mix(texColor.rgb, cloudColor.rgb, cloudMask * uCloudAlpha);;
		}

		if (isEmissive) {
			frag_color = texColor;
			return;
		}

		vec3 norm       = normalize(Normal);
		vec3 lightDir   = normalize(lightPos - FragPos);
		vec3 viewDir    = normalize(viewPos  - FragPos);
		vec3 halfwayDir = normalize(lightDir + viewDir);

		float ambientStrength = 0.05;
		vec3  ambient  = ambientStrength * texColor.rgb;

		float diff    = max(dot(norm, lightDir), 0.0);
		vec3  diffuse = diff * texColor.rgb;

		float spec    = pow(max(dot(norm, halfwayDir), 0.0), uShininess);
		vec3 specular = uSpecStrength * spec * vec3(1.0);

		frag_color = vec4(ambient + diffuse + specular, texColor.a);
	}
"""

VERTEX_SHADER_RING = """
	#version 400
	layout(location = 0) in vec3 aPos;
	layout(location = 1) in vec2 aTex;

	uniform mat4 model;
	uniform mat4 view;
	uniform mat4 proj;

	out vec2 UV;

	void main() {
		UV = aTex;
		gl_Position = proj * view * model * vec4(aPos, 1.0);
	}
"""

FRAGMENT_SHADER_RING = """
	#version 400
	in vec2 UV;
	out vec4 frag_color;

	uniform sampler1D tex_ring;

	void main() {
		vec4 color = texture(tex_ring, UV.x);
		if(color.a < 0.05) discard;
		frag_color = color;
	}
"""

# =============================================================================
# ESTADO GLOBAL
# =============================================================================

window             = None
shader_prog_sphere = None
shader_prog_ring   = None

vao_sphere         = None
num_indices_sphere = 0
vao_ring           = None
num_indices_ring   = 0

sim_time_days = 0.0
frame_delta   = 0.0

loaded_textures    = {}
ring_textures      = {}
ring_texture       = None
default_texture_2d = None
default_texture_1d = None

sim_speed_mult = 1.0

cam_pos   = np.array([0.0, 10.0, 30.0], dtype=np.float32)
cam_yaw   = -90.0
cam_pitch = -20.0

cam_target     = None
orbital_yaw    = 45.0
orbital_pitch  = 20.0
orbital_radius = 5.0

last_mouse_x = WIDTH  / 2
last_mouse_y = HEIGHT / 2
first_mouse  = True

# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

def init_opengl():
	global window

	glfw.init()
	window = glfw.create_window(WIDTH, HEIGHT, WINDOW_TITLE, None, None)
	glfw.make_context_current(window)
	glfw.set_cursor_pos_callback(window, mouse_callback)
	glfw.set_scroll_callback(window, scroll_callback)
	glfw.set_key_callback(window, key_callback)
	glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)

	glEnable(GL_DEPTH_TEST)


def init_shaders():
	global shader_prog_sphere, shader_prog_ring

	vs_sph = OpenGL.GL.shaders.compileShader(VERTEX_SHADER_SPHERE, GL_VERTEX_SHADER)
	fs_sph = OpenGL.GL.shaders.compileShader(FRAGMENT_SHADER_SPHERE, GL_FRAGMENT_SHADER)
	shader_prog_sphere = OpenGL.GL.shaders.compileProgram(vs_sph, fs_sph)

	vs_rng = OpenGL.GL.shaders.compileShader(VERTEX_SHADER_RING, GL_VERTEX_SHADER)
	fs_rng = OpenGL.GL.shaders.compileShader(FRAGMENT_SHADER_RING, GL_FRAGMENT_SHADER)
	shader_prog_ring = OpenGL.GL.shaders.compileProgram(vs_rng, fs_rng)


def init_geometry():
	"""Gera e carrega VAOs da Esfera e dos Anéis."""
	global vao_sphere, num_indices_sphere
	global vao_ring, num_indices_ring

	# --- ESFERA ---
	v_sph, i_sph = _generate_sphere(1.0, SPHERE_SLICES, SPHERE_STACKS)
	num_indices_sphere = len(i_sph)

	vao_sphere = glGenVertexArrays(1)
	glBindVertexArray(vao_sphere)
	
	vbo_sph = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, vbo_sph)
	glBufferData(GL_ARRAY_BUFFER, v_sph.nbytes, v_sph, GL_STATIC_DRAW)
	
	ebo_sph = glGenBuffers(1)
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_sph)
	glBufferData(GL_ELEMENT_ARRAY_BUFFER, i_sph.nbytes, i_sph, GL_STATIC_DRAW)

	stride_sph = 8 * 4
	glEnableVertexAttribArray(0)
	glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride_sph, ctypes.c_void_p(0))
	glEnableVertexAttribArray(1)
	glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride_sph, ctypes.c_void_p(3 * 4))
	glEnableVertexAttribArray(2)
	glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride_sph, ctypes.c_void_p(6 * 4))

	# --- ANÉIS ---
	v_rng, i_rng = _generate_ring(1.2, 2.3, RING_SLICES)
	num_indices_ring = len(i_rng)

	vao_ring = glGenVertexArrays(1)
	glBindVertexArray(vao_ring)

	vbo_rng = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, vbo_rng)
	glBufferData(GL_ARRAY_BUFFER, v_rng.nbytes, v_rng, GL_STATIC_DRAW)

	ebo_rng = glGenBuffers(1)
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_rng)
	glBufferData(GL_ELEMENT_ARRAY_BUFFER, i_rng.nbytes, i_rng, GL_STATIC_DRAW)

	stride_rng = 5 * 4
	glEnableVertexAttribArray(0)
	glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride_rng, ctypes.c_void_p(0))
	glEnableVertexAttribArray(1)
	glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride_rng, ctypes.c_void_p(3 * 4))


def init_textures():
	global default_texture_2d, default_texture_1d, ring_texture, ring_textures

	default_texture_2d = _create_default_texture_2d()
	default_texture_1d = _create_default_texture_1d()
	TEXTURE_DIR.mkdir(exist_ok=True)

	# Texturas esféricas (planetas/céu)
	for name, data in CELESTIAL_BODIES.items():
		path = TEXTURE_DIR / data["tex"]
		loaded_textures[name] = _load_texture_2d(path)

		if "tex_clouds" in data:
			path_clouds = TEXTURE_DIR / data["tex_clouds"]
			loaded_textures[f"{name}_Clouds"] = _load_texture_2d(path_clouds)

	# Textura 1D dos Anéis
	path_saturn_ring = TEXTURE_DIR / "2k_saturn_ring_alpha.png" 
	ring_textures["Saturno"] = _load_texture_1d(path_saturn_ring)

	path_uranus_ring = TEXTURE_DIR / "2k_uranus_ring_alpha.png" 
	ring_textures["Urano"] = _load_texture_1d(path_uranus_ring)

	print(loaded_textures)


def build_projection_matrix():
	fov    = np.radians(FOV_DEG)
	aspect = WIDTH / HEIGHT
	f      = 1.0 / np.tan(fov / 2)
	c      = (Z_FAR + Z_NEAR) / (Z_NEAR - Z_FAR)
	d      = (2 * Z_FAR * Z_NEAR) / (Z_NEAR - Z_FAR)
	return np.array([
		[f / aspect, 0,  0, 0],
		[0,          f,  0, 0],
		[0,          0,  c, d],
		[0,          0, -1, 0],
	], dtype=np.float32)

# =============================================================================
# GEOMETRIA
# =============================================================================
 
def _generate_sphere(radius, slices, stacks):
	vertices, indices = [], []
	for p in range(stacks + 1):
		phi = np.pi * p / stacks
		v   = phi / np.pi
		for f in range(slices + 1):
			theta = 2.0 * np.pi * f / slices
			u     = f / slices
			x = radius * np.sin(phi) * np.cos(theta)
			y = radius * np.cos(phi)
			z = radius * np.sin(phi) * np.sin(theta)

			n_len = np.sqrt(x*x + y*y + z*z)
			nx, ny, nz = (x/n_len, y/n_len, z/n_len) if n_len > 0 else (0.0, 1.0, 0.0)
			vertices.extend([x, y, z, nx, ny, nz, u, v])

	for p in range(stacks):
		for f in range(slices):
			v0 =  p      * (slices + 1) + f
			v1 =  p      * (slices + 1) + f + 1
			v2 = (p + 1) * (slices + 1) + f
			v3 = (p + 1) * (slices + 1) + f + 1
			indices.extend([v0, v2, v1, v1, v2, v3])

	return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)


def _generate_ring(inner_radius, outer_radius, slices):
	vertices, indices = [], []
	for f in range(slices + 1):
		theta = 2.0 * np.pi * f / slices
		cos_t, sin_t = np.cos(theta), np.sin(theta)
		
		# Interno (u=0.0)
		vertices.extend([inner_radius * cos_t, 0.0, inner_radius * sin_t, 0.0, 0.0])
		# Externo (u=1.0)
		vertices.extend([outer_radius * cos_t, 0.0, outer_radius * sin_t, 1.0, 0.0])
		
	for f in range(slices):
		v0 = f * 2
		v1 = f * 2 + 1
		v2 = (f + 1) * 2
		v3 = (f + 1) * 2 + 1
		indices.extend([v0, v1, v2, v2, v1, v3])

	return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)

# =============================================================================
# TEXTURAS
# =============================================================================

def _create_default_texture_2d():
	tex_id = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, tex_id)
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, np.array([255, 255, 255, 255], dtype=np.uint8))
	return tex_id


def _create_default_texture_1d():
	tex_id = glGenTextures(1)
	glBindTexture(GL_TEXTURE_1D, tex_id)
	# Textura fallback semi-transparente para o anel
	glTexImage1D(GL_TEXTURE_1D, 0, GL_RGBA, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, np.array([200, 180, 150, 200], dtype=np.uint8))
	return tex_id


def _load_texture_2d(path):
	try:
		img = Image.open(path).convert("RGBA")
		img_data = np.array(img, dtype=np.uint8)
		tex_id = glGenTextures(1)
		glBindTexture(GL_TEXTURE_2D, tex_id)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
		glGenerateMipmap(GL_TEXTURE_2D)
		return tex_id
	except FileNotFoundError:
		return default_texture_2d


def _load_texture_1d(path):
	try:
		img      = Image.open(path).convert("RGBA")
		img_data = np.array(img, dtype=np.uint8)
		tex_id   = glGenTextures(1)
		glBindTexture(GL_TEXTURE_1D, tex_id)
		glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
		glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
		glTexImage1D(GL_TEXTURE_1D, 0, GL_RGBA, img.width, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
		glGenerateMipmap(GL_TEXTURE_1D)
		return tex_id
	except FileNotFoundError:
		return default_texture_1d

# =============================================================================
# MATEMÁTICA E TRANSFORMAÇÕES
# =============================================================================

def _translate(x, y, z):
	return np.array([[1,0,0,x], [0,1,0,y], [0,0,1,z], [0,0,0,1]], dtype=np.float32)


def _scale_uniform(s):
	return np.array([[s,0,0,0], [0,s,0,0], [0,0,s,0], [0,0,0,1]], dtype=np.float32)


def _rotate_y(deg):
	rad  = np.radians(deg)
	c, s = np.cos(rad), np.sin(rad)
	return np.array([[c,0,s,0], [0,1,0,0], [-s,0,c,0], [0,0,0,1]], dtype=np.float32)


def _rotate_z(deg):
	rad  = np.radians(deg)
	c, s = np.cos(rad), np.sin(rad)
	return np.array([[c,-s,0,0], [s,c,0,0], [0,0,1,0], [0,0,0,1]], dtype=np.float32)


def _look_at(eye, center, up):
	f = center - eye
	f_norm = np.linalg.norm(f)
	if f_norm == 0: return np.identity(4, dtype=np.float32)
	f /= f_norm
	
	s = np.cross(f, up)
	s_norm = np.linalg.norm(s)
	if s_norm == 0: return np.identity(4, dtype=np.float32)
	s /= s_norm
	
	u = np.cross(s, f)
	view = np.identity(4, dtype=np.float32)
	view[0,:3] = s;  view[0,3] = -np.dot(s, eye)
	view[1,:3] = u;  view[1,3] = -np.dot(u, eye)
	view[2,:3] = -f; view[2,3] =  np.dot(f, eye)
	return view


def _fps_front_vector():
	front = np.array([
		np.cos(np.radians(cam_yaw)) * np.cos(np.radians(cam_pitch)),
		np.sin(np.radians(cam_pitch)),
		np.sin(np.radians(cam_yaw)) * np.cos(np.radians(cam_pitch)),
	])
	return front / np.linalg.norm(front)


def _scaled_radius(name):
	r_base = CELESTIAL_BODIES[name]["r"]
	return r_base


def _scaled_distance(name):
	return CELESTIAL_BODIES[name]["d"]

# =============================================================================
# SIMULAÇÃO ORBITAL & CÂMERA
# =============================================================================

def compute_model_matrix(name, current_cam_pos, earth_orbital_matrix):
	data = CELESTIAL_BODIES[name]

	if name == "Skybox":
		return _translate(*current_cam_pos) @ _scale_uniform(data["r"])

	ang_orbit    = (sim_time_days / data["orb"] * 360.0) if data["orb"] > 0 else 0.0
	ang_rotation = (sim_time_days / (data["rot"] / 24.0) * 360.0)
	
	dist   = _scaled_distance(name)
	radius = _scaled_radius(name)

	if name == "Lua":
		T_orbital_moon = _rotate_y(ang_orbit) @ _translate(dist, 0, 0)
		T_world_matrix = earth_orbital_matrix @ T_orbital_moon
		world_x, world_y, world_z = T_world_matrix[0, 3], T_world_matrix[1, 3], T_world_matrix[2, 3]
	else:
		T_orbital = _rotate_y(ang_orbit) @ _translate(dist, 0, 0)
		world_x, world_y, world_z = T_orbital[0, 3], T_orbital[1, 3], T_orbital[2, 3]
	
	matrix = _translate(world_x, world_y, world_z
	) @ _rotate_z(data["tilt"]) @ _rotate_y(ang_rotation) @ _scale_uniform(radius)

	return matrix


def precompute_world_positions(current_cam_pos):
	world_positions = {}
	earth_orbital_mat = None

	for name in CELESTIAL_BODIES:
		if name == "Terra":
			data              = CELESTIAL_BODIES[name]
			ang_orbit         = (sim_time_days / data["orb"] * 360.0) if data["orb"] > 0 else 0.0
			earth_orbital_mat = _rotate_y(ang_orbit) @ _translate(_scaled_distance("Terra"), 0, 0)

		model                 = compute_model_matrix(name, current_cam_pos, earth_orbital_mat)
		world_positions[name] = (model @ np.array([0, 0, 0, 1]))[:3]

	return world_positions, earth_orbital_mat


def _orbital_cam_position(target_pos):
	yaw_r   = np.radians(orbital_yaw)
	pitch_r = np.radians(orbital_pitch)
	offset  = orbital_radius * np.array([
		np.cos(pitch_r) * np.sin(yaw_r),
		np.sin(pitch_r),
		np.cos(pitch_r) * np.cos(yaw_r),
	])
	return target_pos + offset


def compute_camera_view(world_positions):
	global cam_pos
	if cam_target is not None:
		target_pos = world_positions[cam_target]
		cam_pos    = _orbital_cam_position(target_pos)
		return _look_at(cam_pos, target_pos, np.array([0.0, 1.0, 0.0]))

	front = _fps_front_vector()
	return _look_at(cam_pos, cam_pos + front, np.array([0.0, 1.0, 0.0]))

# =============================================================================
# RENDERIZAÇÃO
# =============================================================================

def render_body(name, model_matrix, cloud_offset=0.0, alpha_offset=1.0):
	glUseProgram(shader_prog_sphere)
	
	loc_model = glGetUniformLocation(shader_prog_sphere, "model")
	glUniformMatrix4fv(loc_model, 1, GL_TRUE, model_matrix)
	
	loc_emissive = glGetUniformLocation(shader_prog_sphere, "isEmissive")
	glUniform1i(loc_emissive, int(name in EMISSIVE_BODIES))

	# Material específico por planeta
	spec_strength, shininess = MATERIAL[name]
	glUniform1f(glGetUniformLocation(shader_prog_sphere, "uSpecStrength"), spec_strength)
	glUniform1f(glGetUniformLocation(shader_prog_sphere, "uShininess"),    shininess    )

	loc_use_clouds = glGetUniformLocation(shader_prog_sphere, "useClouds")
	cloud_tex_name = f"{name}_Clouds"

	if cloud_tex_name in loaded_textures:
		glUniform1i(loc_use_clouds, 1)
		glUniform1f(glGetUniformLocation(shader_prog_sphere, "uCloudOffset"), cloud_offset)
		
		glUniform1f(glGetUniformLocation(shader_prog_sphere, "uCloudAlpha"), alpha_offset)

		glActiveTexture(GL_TEXTURE1)
		glBindTexture(GL_TEXTURE_2D, loaded_textures[f"{name}_Clouds"])
		glUniform1i(glGetUniformLocation(shader_prog_sphere, "tex_clouds"), 1)
	else:
		glUniform1i(loc_use_clouds, 0)

	glActiveTexture(GL_TEXTURE0)
	glBindTexture(GL_TEXTURE_2D, loaded_textures[name])
	glUniform1i(glGetUniformLocation(shader_prog_sphere, "tex_diffuse"), 0)

	glBindVertexArray(vao_sphere)
	if name == "Skybox":
		glDepthMask(GL_FALSE)
		glDrawElements(GL_TRIANGLES, num_indices_sphere, GL_UNSIGNED_INT, None)
		glDepthMask(GL_TRUE)
	else:
		glDrawElements(GL_TRIANGLES, num_indices_sphere, GL_UNSIGNED_INT, None)


def render_ring(model_matrix, view_matrix, proj_matrix, ring_tex_id):
	glUseProgram(shader_prog_ring)
	
	# Prepara uniforms
	loc_model = glGetUniformLocation(shader_prog_ring, "model")
	glUniformMatrix4fv(loc_model, 1, GL_TRUE, model_matrix)
	
	loc_view = glGetUniformLocation(shader_prog_ring, "view")
	glUniformMatrix4fv(loc_view, 1, GL_TRUE, view_matrix)
	
	loc_proj = glGetUniformLocation(shader_prog_ring, "proj")
	glUniformMatrix4fv(loc_proj, 1, GL_TRUE, proj_matrix)

	glActiveTexture(GL_TEXTURE0)
	glBindTexture(GL_TEXTURE_1D, ring_tex_id)
	glUniform1i(glGetUniformLocation(shader_prog_ring, "tex_ring"), 0)

	glBindVertexArray(vao_ring)
	glEnable(GL_BLEND)

	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	glDisable(GL_CULL_FACE)
	glDrawElements(GL_TRIANGLES, num_indices_ring, GL_UNSIGNED_INT, None)
	
	glDisable(GL_BLEND)


def render_frame(proj_matrix):
	world_positions, earth_orbital_mat = precompute_world_positions(cam_pos)
	view = compute_camera_view(world_positions)

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glViewport(0, 0, WIDTH, HEIGHT)

	# Configura globais do shader de esfera
	glUseProgram(shader_prog_sphere)
	glUniformMatrix4fv(glGetUniformLocation(shader_prog_sphere, "view"), 1, GL_TRUE, view)
	glUniformMatrix4fv(glGetUniformLocation(shader_prog_sphere, "proj"), 1, GL_TRUE, proj_matrix)
	glUniform3f(glGetUniformLocation(shader_prog_sphere, "viewPos"), * cam_pos)
	glUniform3f(glGetUniformLocation(shader_prog_sphere, "lightPos"), 0.0, 0.0, 0.0)

	# 1. Renderiza os planetas
	saturn_model = None
	uranus_model = None
	cloud_offset, alpha_offset = 0.0, 1.0

	for name in RENDER_ORDER:
		model = compute_model_matrix(name, cam_pos, earth_orbital_mat)
		if name == "Saturno":
			saturn_model = model

		if name == "Urano":
			uranus_model = model

		if name == "Terra":
			cloud_offset = sim_time_days * 0.07
			alpha_offset = 1.5

		if name == "Venus":
			cloud_offset = sim_time_days * 0.025
			alpha_offset = 1.0
		
		render_body(name, model, cloud_offset, alpha_offset)

	# 2. Renderiza os Anéis
	if saturn_model is not None:
		render_ring(saturn_model, view, proj_matrix, ring_textures["Saturno"])

	if uranus_model is not None:
		render_ring(uranus_model, view, proj_matrix, ring_textures["Urano"])

# =============================================================================
# CALLBACKS E MODO FOCO
# =============================================================================

def mouse_callback(window, xpos, ypos):
	global last_mouse_x, last_mouse_y, first_mouse, cam_yaw, cam_pitch, orbital_yaw, orbital_pitch

	if first_mouse:
		last_mouse_x, last_mouse_y = xpos, ypos
		first_mouse = False
		return

	dx = (xpos - last_mouse_x) * CAM_SENSITIVITY
	dy = (last_mouse_y - ypos) * CAM_SENSITIVITY
	last_mouse_x, last_mouse_y = xpos, ypos

	if cam_target is None:
		cam_yaw   += dx
		cam_pitch  = max(-89.0, min(89.0, cam_pitch + dy))
	else:
		orbital_yaw   += dx * (ORBITAL_SENSITIVITY / CAM_SENSITIVITY)
		orbital_pitch  = max(-89.0, min(89.0, orbital_pitch + dy * (ORBITAL_SENSITIVITY / CAM_SENSITIVITY)))


def scroll_callback(window, xoffset, yoffset):
	global orbital_radius
	if cam_target is None: return

	radius = _scaled_radius(cam_target)
	if radius <= 0:	return

	# Define o multiplicador da distância mínima com base no tamanho do planeta
	if radius < 0.04:
		min_dist = radius * 3.9
	elif radius < 0.12:
		min_dist = radius * 3.4
	else:
		min_dist = radius * 2.0

	max_dist = radius * 500.0

	orbital_radius *= (1.0 - yoffset * ORBITAL_ZOOM_SPEED)
	orbital_radius = float(np.clip(orbital_radius, min_dist, max_dist))


def _enter_focus_mode(planet_name):
	global cam_target, first_mouse
	global orbital_yaw, orbital_pitch, orbital_radius

	cam_target  = planet_name
	first_mouse = True
	
	orbital_radius = _scaled_radius(planet_name) * 4
	orbital_yaw    = 45.0
	orbital_pitch  = 20.0


def key_callback(window, key, scancode, action, mode):
	global cam_target, first_mouse, sim_speed_mult, radius_scale

	if action != glfw.PRESS: return

	if key == glfw.KEY_ESCAPE: glfw.set_window_should_close(window, True)
	elif key == glfw.KEY_SPACE:
		cam_target, first_mouse = None, True
	elif key in KEY_PLANET_MAP:
		_enter_focus_mode(KEY_PLANET_MAP[key])
		
	elif key == glfw.KEY_L: sim_speed_mult += SIM_SPEED_STEP
	elif key == glfw.KEY_K: sim_speed_mult = max(SIM_SPEED_MIN, sim_speed_mult - SIM_SPEED_STEP)
	elif key == glfw.KEY_J: sim_speed_mult = 1.0


def process_free_camera(delta_time):
	global cam_pos
	if cam_target is not None: return

	speed = CAM_SPEED * delta_time
	front = _fps_front_vector()
	right = np.cross(front, np.array([0.0, 1.0, 0.0]))
	right /= np.linalg.norm(right)

	if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS: cam_pos += front * speed
	if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS: cam_pos -= front * speed
	if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS: cam_pos -= right * speed
	if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS: cam_pos += right * speed

# =============================================================================
# MAIN LOOP
# =============================================================================

def run():
	global sim_time_days, frame_delta
	proj_matrix = build_projection_matrix()
	prev_time   = glfw.get_time()

	while not glfw.window_should_close(window):
		current_time = glfw.get_time()
		frame_delta  = current_time - prev_time
		prev_time    = current_time

		sim_time_days += frame_delta * DEFAULT_SIM_SPEED * sim_speed_mult
		
		process_free_camera(frame_delta)
		render_frame(proj_matrix)

		glfw.swap_buffers(window)
		glfw.poll_events()

	glfw.terminate()


def print_controls():
	print("""\n\n\n
		======================== CONTROLES ========================

		W / A / S / D         - Movimentação da câmera (modo livre)
		Mouse                 - Rotação da câmera (modo livre)
		1–0                   - Foca a câmera no planeta correspondente
		SPACE                 - Retorna ao modo de câmera livre
		ESC                   - Fecha a janela

			  --- Velocidade da simulação ---
		L                     - Aumenta velocidade (+10×)
		K                     - Diminui velocidade (-10×)
		J                     - Velocidade padrão (reset)

			 --- Modo de foco (câmera orbital) ---
		Mouse                 - Orbita ao redor do planeta
		Scroll do mouse       - Zoom in / out


		DICA: Se quiser aumentar o tamanho dos planetas para melhor visualização, 
		altere a variável `radius_scale`(linha 90) no início do código (ex: `radius_scale = 7.0`).
		===========================================================\n\n\n
""")


def main():
	os.system('cls' if os.name == 'nt' else 'clear')
	init_opengl()
	init_shaders()
	init_geometry()
	init_textures()
	print_controls()
	run()


if __name__ == "__main__":
	main()