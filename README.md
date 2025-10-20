# 👁️ sinaliza_vision_backend

## Módulo Central de Visão Computacional (Libras Gameficado)

Este repositório hospeda o **Módulo de Visão Computacional** do projeto **Sinaliza App**, um aplicativo focado no aprendizado gamificado de Libras (Língua Brasileira de Sinais).

Este módulo é o coração do sistema de reconhecimento, responsável por processar a entrada de vídeo/câmera e traduzir os gestos do usuário em dados interpretáveis para o backend principal.

---

### 💡 Objetivos e Funcionalidades

Nosso objetivo principal é garantir o reconhecimento de sinais de forma precisa e eficiente para um ambiente de aprendizado gamificado.

* **Detecção de Gesto/Sinal:** Identificação e classificação de diferentes sinais de Libras (ex: letras, palavras básicas).
* **Rastreamento de Mãos e Corpo:** Utilização do MediaPipe para obter *landmarks* (pontos chave) de alta precisão do corpo e das mãos.
* **Extração de Features:** Pré-processamento dos dados dos *landmarks* para criação de vetores de características prontos para o modelo de classificação (IA).
* **Integração de API:** Fornecer *endpoints* robustos e de baixa latência para o consumo pelo backend/frontend principal.
* **Performance:** Garantir que o processamento seja rápido o suficiente para uma experiência em tempo real.

### 🛠️ Tecnologias Utilizadas

Este módulo é construído sobre ferramentas líderes em visão computacional e Machine Learning:

| Tecnologia | Função |
| :--- | :--- |
| **Python** | Linguagem principal de desenvolvimento. |
| **MediaPipe** | Framework essencial para detecção de *landmarks* de mãos e pose. |
| **OpenCV** | Manipulação de imagens e pré-processamento de frames.
#### 2. Clonar o Repositório
git clone [https://github.com/luizpadilha-collab/sinaliza_vision_backend.git](https://github.com/luizpadilha-collab/sinaliza_vision_backend.git)
cd sinaliza_vision_backend
