# 👁️ Arquitetura do Módulo de Visão Computacional (Sinaliza App)

Este documento explica como funciona a arquitetura de Inteligência Artificial e Visão Computacional do **Sinaliza App**. O sistema é dividido em duas abordagens principais para resolver problemas diferentes de tradução da Língua Brasileira de Sinais (Libras).

---

## 🗺️ Visão Geral da Arquitetura

O sistema é desenhado de forma híbrida para otimizar a detecção de acordo com a natureza do sinal:

```mermaid
graph TD
    subgraph Entrada ["Entrada (Webcam / App Flutter)"]
        Video["Fluxo de Vídeo (Câmera)"]
    end

    subgraph Abordagem1 ["Abordagem 1: Reconhecimento Estático (YOLO)"]
        Video -->|1 Frame Isolado| YOLO["Modelo YOLOv8 (.pt / .onnx)"]
        YOLO -->|Classificação de Pose Estática| Letra["Letra do Alfabeto (A, B, C...)"]
    end

    subgraph Abordagem2 ["Abordagem 2: Reconhecimento Dinâmico (MediaPipe + LSTM)"]
        Video -->|Sequência de 30 Frames| MP["MediaPipe Holistic"]
        MP -->|Pontos Chave (Keypoints)| NPY["Vetores de Coordenadas (.npy)"]
        NPY -->|Série Temporal (Tempo)| LSTM["Rede Neural LSTM / GRU"]
        LSTM -->|Classificação de Movimento| Expressao["Expressão/Palavra (comer, beber, bom dia...)"]
    end

    Letra --> Saida["Saída de Dados (API / WebSocket)"]
    Expressao --> Saida
```

---

## 📦 Abordagem 1: Letras do Alfabeto (Reconhecimento Estático com YOLO)

*   **Objetivo:** Detectar e classificar as letras do alfabeto manual de Libras (ex: as configurações de mão para as letras A, B, C...).
*   **Modelo Utilizado:** YOLOv8 (You Only Look Once).
*   **Funcionamento:** 
    1. O aplicativo envia um frame isolado da câmera (uma imagem estática) via WebSocket ou requisição POST HTTP.
    2. O servidor passa a imagem pelo modelo YOLO.
    3. O YOLO analisa os padrões visuais espaciais (texturas, contornos, formato da mão) diretamente na imagem, localiza a mão e classifica instantaneamente qual é a letra correspondente.
*   **Vantagens:** Altíssima velocidade de inferência (FPS alto), ótimo para rodar em servidores simples ou direto no celular, muito preciso para formas estáticas.
*   **Limitação:** O YOLO convencional não compreende a dimensão do tempo. Ele não consegue diferenciar um sinal dinâmico que exige movimento (como "beber") de outro sinal de formato parecido, pois ele só olha fotos congeladas.

---

## 🔄 Abordagem 2: Expressões e Palavras (Reconhecimento Dinâmico com MediaPipe + LSTM)

*   **Objetivo:** Reconhecer sinais dinâmicos que envolvem movimentos e expressões completas (ex: "comer", "beber", "bom dia", "ajuda").
*   **Modelos Utilizados:** MediaPipe Holistic + Rede Neural Recorrente (LSTM ou GRU).
*   **Funcionamento:**
    1. **Fase de Extração (MediaPipe):** Em vez de processar imagens coloridas pesadas, a câmera captura uma sequência temporal de 30 frames (cerca de 1 segundo de ação). Para cada frame, o MediaPipe extrai apenas as coordenadas geométricas 3D $(X, Y, Z)$ das articulações do corpo (pose), dos dedos das mãos e do rosto.
    2. **Fase de Compactação:** O script `coletar_dados.py` descarta a imagem de vídeo e salva apenas estes pontos de coordenadas geométricas (os *keypoints*) em arquivos numpy (`.npy`). Isso transforma dados visuais pesados em pequenos vetores matemáticos ultra leves.
    3. **Fase de Classificação Temporal (LSTM):** A sequência de 30 vetores ordenados no tempo é enviada para uma rede neural recorrente (LSTM). A rede analisa a trajetória desses pontos ao longo do tempo (ex: a mão esquerda subindo em direção à boca) para deduzir o significado do gesto completo.
*   **Vantagens:** 
    *   **Imunidade a ruídos visuais:** A rede neural do classificador (LSTM) não vê cores, iluminação ou o fundo da imagem. Ela só vê a "estrutura de arame" das mãos e do corpo, tornando o modelo muito robusto.
    *   **Compreensão temporal:** Consegue aprender o início, meio e fim de um gesto dinâmico.

---

## ⚙️ Resumo das Diferenças

| Característica | Abordagem 1 (YOLO) | Abordagem 2 (MediaPipe + LSTM) |
| :--- | :--- | :--- |
| **Tipo de Sinal** | Estático (Letras do Alfabeto) | Dinâmico (Expressões / Palavras) |
| **Dado de Entrada** | Imagem inteira (Matriz RGB) | Coordenadas geométricas ($X, Y, Z$) |
| **Fator Tempo** | Não considera (Analisa frame a frame) | Essencial (Analisa sequências de 30 frames) |
| **Processamento** | Mais pesado por frame (Rede Convolucional) | Mais leve (Rede LSTM processando números simples) |
| **Sensibilidade** | Depende de boa iluminação e foco | Depende apenas da precisão do rastreio de pontos |
