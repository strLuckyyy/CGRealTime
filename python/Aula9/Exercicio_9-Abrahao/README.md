# Simulador do Sistema Solar em OpenGL

Trabalho final abordando a simulação 3D do Sistema Solar utilizando Python e OpenGL moderno. 

## Como executar

Para rodar o projeto, você precisa do Python instalado e das bibliotecas listadas abaixo.
Você pode instalar tudo de uma vez rodando:

```bash
pip install PyOpenGL PyOpenGL_accelerate glfw Pillow numpy


python "Aula 9 - Exercicio.py"
```

## Bibliotecas Utilizadas
- **PyOpenGL / PyOpenGL_accelerate:** Para o acesso às funções e shaders do OpenGL moderno.
- **glfw:** Para criação da janela, contexto do OpenGL e captura de inputs (teclado e mouse).
- **Pillow (PIL):** Para o carregamento e manipulação das imagens de textura.
- **numpy:** Para otimização dos cálculos matemáticos, matrizes de transformação e envio eficiente de dados para a GPU.

## Controles
O simulador possui dois modos de câmera: Modo Livre e Modo de Foco (Orbital).

**Câmera Livre:**
- **W / A / S / D:** Movimenta a câmera pelo espaço.
- **Mouse:** Gira a visão da câmera.

**Modo de Foco (Planetas):**
- **1 a 0:** Foca a câmera em um astro específico (1 = Sol, 4 = Terra, 5 = Lua, etc.).
- **Mouse:** Orbita ao redor do astro focado.
- **Scroll do Mouse:** Aproxima (Zoom in) ou afasta (Zoom out) do astro.
- **SPACE:** Sai do modo de foco e retorna para a câmera livre.

**Controle de Tempo:**
- **L:** Acelera a simulação (+10x).
- **K:** Desacelera a simulação (-10x).
- **J:** Reseta a velocidade para o padrão.

**Outros:**
- **ESC:** Fecha o simulador.

## Escalas Adotadas
O sistema foi construído mantendo a proporção real ditada pelo exercício, utilizando as seguintes regras matemáticas para os cálculos de renderização:

**Translação/Distância:** O valor base da renderização equivale à distância real em milhões de quilômetros (distância_render = distância_real_em_milhões_de_km).

**Escala/Raio:** O tamanho do planeta em cena equivale ao raio real dividido por 50.000 (raio_render = raio_real_em_km / 50000).

**Nota:** Para melhor visualização na cena, incluí uma variável no código chamada radius_scale, que permite multiplicar o tamanho visual dos planetas de forma uniforme sem quebrar a proporção entre eles.

## Fontes das Texturas
As texturas dos planetas, da lua, skybox e aneis foram retiradas do site https://www.solarsystemscope.com/textures/.

O anel de Urano é apenas o anel de Saturno de outra cor. Modificado no programa Photopea. https://www.photopea.com/