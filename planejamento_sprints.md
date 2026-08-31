# 📋 Planejamento de Sprints - Visão Computacional (Sinaliza App)
## Disciplina: PIEC3 (1ª VA)

Este documento descreve a divisão de tarefas (backlog) em 3 sprints de 15 dias cada para a primeira avaliação (1ª VA). O foco foi alterado para unificar a arquitetura de IA: **abandonamos o YOLO para o alfabeto e criaremos um classificador próprio baseado em Keypoints (MediaPipe)**. Assim, todo o processamento móvel e web dependerá de um único extrator de coordenadas leve e eficiente.

---

## 🏃 Sprint 1: Normalização Relativa e Novo Modelo de Alfabeto (Keypoints)
* **Período:** Dias 1 a 15
* **Meta da Sprint:** Desenvolver a normalização de coordenadas e coletar/treinar o novo modelo do alfabeto de A a Z utilizando apenas pontos chave das mãos e corpo, corrigindo gestos incorretos e eliminando o modelo YOLO.

### 📝 Backlog de Tarefas:
* [x] **Task 1.1: Função de Normalização de Mãos e Pose (Wrist & Shoulder Centered)**
  * *Descrição:* Codificar as funções matemáticas para centralizar os pontos da mão no punho e os pontos do corpo nos ombros, escalonando proporcionalmente.
  * *Critério de Aceitação:* Testar funções com vetores de teste e obter formas invariantes à escala.
* [x] **Task 1.2: Atualização do Coletor de Dados para Alfabeto**
  * *Descrição:* Ajustar o [coletar_dados.py](file:///c:/Users/Notebook/Documents/Sinaliza_vision_backend/coletar_dados.py) para suportar a coleta dos gestos estáticos das 26 letras (A-Z) com normalização automática.
  * *Critério de Aceitação:* Gravar frames de teste salvando keypoints normalizados de letras.
* [x] **Task 1.3: Criação do Dataset de Libras do Alfabeto**
  * *Descrição:* Coletar as configurações de mão corretas para o alfabeto de A a Z de Libras (corrigindo distorções do dataset anterior).
  * *Critério de Aceitação:* Dataset do alfabeto completo com 30 repetições por letra.
* [x] **Task 1.4: Modelo de Classificação e Treino do Alfabeto**
  * *Descrição:* Criar o script `treinar_alfabeto.py` para treinar uma rede neural densa (MLP) em PyTorch para classificar as 26 letras baseadas nos keypoints normalizados de um único frame.
  * *Critério de Aceitação:* Acurácia do classificador do alfabeto $> 90\%$ em validação.
* [ ] **Task 1.5: Treinamento e Teste Inicial do Modelo de Expressões Dinâmicas (Fim de Semana)**
  * *Descrição:* Executar e validar o script `treinar_lstm.py` com o dataset dinâmico de expressões (palavras), aplicando a nova normalização geométrica de pose/mãos, e realizar testes em tempo real via `testar_lstm.py`.
  * *Critério de Aceitação:* Obter convergência no treinamento do modelo LSTM e validar a inferência em tempo real com taxa aceitável de acertos.

---

## 🏃 Sprint 2: Conversão de Dataset Antigo e Treinamento de Sinais Dinâmicos
* **Período:** Dias 16 a 30
* **Meta da Sprint:** Tratar o dataset dinâmico antigo com a nova normalização, treinar o classificador LSTM para expressões e exportar ambos os modelos (Alfabeto e Expressões) para o formato universal ONNX.

### 📝 Backlog de Tarefas:
* [x] **Task 2.1: Estruturação do Dataset e Loop de Feedback (Autoaperfeiçoamento)**
  * *Descrição:* Reestruturar o dataset em pastas de treinamento versionadas (`v1`, `v2`) e feedback (`bruto/processado/manifesto`), implementar o banco de dados SQLite de feedbacks (`database.py`), a API REST (`feedback_api.py`), o utilitário de curadoria (`curator.py`) e o script de promoção (`promover_dataset.py`).
  * *Critério de Aceitação:* Armazenamento de keypoints brutos de feedback com banco SQLite, curadoria com remoção física de dados rejeitados, promoção imutável com atualização automática do `CHANGELOG.md` e suporte ao parâmetro de versão do dataset no treinamento.
* [ ] **Task 2.2: Treino e Teste da LSTM de Sinais Dinâmicos**
  * *Descrição:* Rodar o [treinar_lstm.py](file:///c:/Users/Notebook/Documents/Sinaliza_vision_backend/treinar_lstm.py) com os dados dinâmicos normalizados e validar em tempo real usando o [testar_lstm.py](file:///c:/Users/Notebook/Documents/Sinaliza_vision_backend/testar_lstm.py).
  * *Critério de Aceitação:* Classificação precisa das expressões com o usuário em diferentes distâncias.
* [ ] **Task 2.3: Exportação dos Modelos para ONNX**
  * *Descrição:* Criar o script `exportar_onnx.py` para converter os dois modelos (MLP do alfabeto e LSTM das expressões) de PyTorch `.pth` para o formato universal `.onnx`.
  * *Critério de Aceitação:* Geração dos arquivos `.onnx` prontos para mobile.

---

## 🏃 Sprint 3: Integração no Flutter (On-Device) e Protótipo Web
* **Período:** Dias 31 a 45
* **Meta da Sprint:** Inserir a execução dos modelos locais no Flutter eliminando a latência do servidor, e criar um protótipo Web leve rodando a classificação local no navegador.

### 📝 Backlog de Tarefas:
* [ ] **Task 3.1: Arquitetura de Integração no Flutter (Dart)**
  * *Descrição:* Desenvolver o guia e código Dart para carregar os modelos `.onnx` via `onnxruntime_flutter` e interligá-los com a câmera e o MediaPipe local.
  * *Critério de Aceitação:* Fluxo funcionando offline no app mobile.
* [ ] **Task 3.2: Protótipo de Classificação Local na Web**
  * *Descrição:* Desenvolver uma página HTML/JS estática usando o MediaPipe JS e ONNX Runtime Web para rodar o modelo do alfabeto e das expressões direto no navegador.
  * *Critério de Aceitação:* Reconhecimento funcional rodando 100% no lado do cliente (browser).
* [ ] **Task 3.3: Consolidação da Documentação e Entrega da 1ª VA**
  * *Descrição:* Atualizar a documentação do repositório, gerar relatórios de testes de performance (latência de inferência local vs. servidor) e preparar a entrega.
