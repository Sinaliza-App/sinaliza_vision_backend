# 📦 Relatório Individual de Entrega de Artefatos de Código — 1ª VA (2026.2)

**Disciplina:** PIEC-3 (Projeto Integrado de Engenharia de Computação 3)  
**Professor:** Waldemar Pires Ferreira Neto  
**Aluno:** Emanuel Khalil Fernandes Novaes Angelim  
**Período:** 2026.2 (1ª Avaliação)  
**Projeto:** Plataforma SINALIZA  

---

## 🔗 1. Repositórios e Branches das Funcionalidades Desenvolvidas

Todos os artefatos de código implementados por mim durante as três sprints da 1ª VA estão versionados e disponíveis nos seguintes repositórios da organização:

1. **Web Dashboard & Laboratório de IA (Criado 100% por mim nesta VA):**
   * **Repositório:** [https://github.com/Sinaliza-App/sinaliza_web_dashboard](https://github.com/Sinaliza-App/sinaliza_web_dashboard)
   * **Branch Principal de Entrega:** `main` (e `Khalil_develop`)
2. **Aplicativo Mobile (Flutter):**
   * **Repositório:** [https://github.com/Sinaliza-App/sinaliza_app_libras](https://github.com/Sinaliza-App/sinaliza_app_libras)
   * **Branch Principal de Entrega:** `khalil_develop`
3. **Backend API & Migrações de Banco de Dados:**
   * **Repositório:** [https://github.com/Sinaliza-App/sinaliza_vision_backend](https://github.com/Sinaliza-App/sinaliza_vision_backend)
   * **Branch Principal de Entrega:** `Khalil_develop` (subdiretório `api_server/`)

---

## 🎯 2. Descrição Geral das Minhas Contribuições na 1ª VA

Durante a 1ª VA (2026.2), atuei na concepção, arquitetura e codificação de quatro frentes essenciais do ecossistema SINALIZA:

1. **Criação do Portal Web de Gestão (React + Tailwind + Vite):** Desenvolvi do zero toda a aplicação web voltada aos professores e administradores, incluindo autenticação com permissões RLS, gráficos analíticos em tempo real, gerenciamento de comunidade, moderação de denúncias, CRUD completo de lições com sistema de rascunhos e o laboratório web de testes de IA.
2. **Nova Visão Computacional On-Device no Aplicativo Mobile (Flutter + Edge AI):** Na sprint final, integrei a execução local dos modelos neurais V2 via ONNX Runtime no Flutter, eliminando a dependência de servidores de inferência, além de criar a compensação matemática de distorção de aspecto da câmera e o algoritmo determinístico para alunos canhotos e destros.
3. **Novos Módulos e Recursos no App Mobile:** Desenvolvi o **Desafio Final de Cada Módulo (Boss Challenge)** com desbloqueio dinâmico e status de "Módulo Dominado", o desacoplamento arquitetural entre Quiz Teórico e Desafio Prático, o canal de envio de reports pelos estudantes, persistência local em SQLite offline, telas criptografadas de recuperação de senha e autenticação social via OAuth.
4. **Backend e Banco de Dados (Node.js/Express & PostgreSQL/Supabase):** Modelei as migrações SQL V2, políticas de Row Level Security (RLS) e endpoints REST para reports, drafts e persistência independente de progresso.

---

## 💻 3. Detalhamento das Funcionalidades Implementadas por Repositório

### A. Repositório: `sinaliza_app_libras` (Aplicativo Mobile Flutter)
Novas funcionalidades, robustez de dados e inferência local no smartphone:

* **Desafio Prático Final de Cada Módulo ("Boss Challenge" - `lib/views/lesson_list_screen.dart`):**
  * Implementação do card especial de fechamento de módulo no rodapé da listagem de lições, com lógica de desbloqueio condicional: só fica disponível quando o aluno conclui 100% das lições válidas daquele módulo.
  * **Três Estados Visuais Reativos:**
    * *Bloqueado:* Card em cinza com ícone de cadeado (`lock_rounded`) e bloqueio de toque com aviso via Snackbar.
    * *Desbloqueado:* Gradiente de fogo laranja/amarelo neon (`local_fire_department_rounded`) com chamada *"Prove que domina o módulo!"*.
    * *Concluído / Dominado:* Gradiente esmeralda com borda dourada, ícone de troféu (`emoji_events_rounded`) e badge permanente *"Módulo Dominado! 🏆"*.
  * **Sorteio Dinâmico:** Seleção e embaralhamento aleatório de até 8 sinais do módulo em execução, abrindo o `ChallengeSequenceScreen` vinculado ao `moduleId`.
* **[US17] Inferência de Visão Computacional On-Device (100% Offline):**
  * `lib/services/libras_inference_service.dart`: Carregamento e execução dos modelos `.onnx` via `onnxruntime` nativo no smartphone. Latência de inferência em tempo real de apenas **~4 ms**, operando sem conexão de internet e com consumo zero de plano de dados.
* **[US19] Correção Geométrica de Aspect Ratio (3:4 vs 4:3):**
  * Implementação de escalonamento anisotrópico nos eixos X, Y e Z dos keypoints antes do repasse ao modelo neural, eliminando a distorção e o achatamento provocados pelo uso do smartphone na vertical.
* **[US20] Algoritmo Dual-Candidate para Destros e Canhotos:**
  * Algoritmo determinístico que avalia simultaneamente o arranjo natural dos pontos das mãos e o arranjo com slots espelhados (esquerda/direita trocados), selecionando o candidato de maior confiança e garantindo inclusão total sem penalizar estudantes canhotos.
* **[US21] Extração Híbrida Assíncrona de Pose e Mãos via Google ML Kit:**
  * `lib/services/vision_extractor_service.dart`: Paralelismo assíncrono com **Dart Isolates**, garantindo captura e processamento a 30 FPS contínuos sem congelar a thread de interface gráfica (UI) do Flutter.
* **[US22] & [US23] Desafio Prático Sequencial e Desacoplamento:**
  * `lib/views/challenge_sequence_screen.dart` e `challenge_flow_screen.dart`: Modo de prática com cronômetro regressivo, detecção de acerto imediata pelo modelo On-Device e transição dinâmica com barra neon.
  * Desacoplamento arquitetural no banco e no app entre o Desafio Prático e o Quiz Teórico (`challenge_progress` vs `quiz_progress`), permitindo que ambos os fluxos avancem sem sobrescrever pontuações.
* **[US24] Quiz Teórico de Múltipla Escolha com Feedback Conceitual:**
  * `lib/views/theoretical_quiz_screen.dart`: Questões gramaticais e conceituais de LIBRAS com embaralhamento aleatório de alternativas, validação visual instantânea e cômputo de XP.
* **[US28] Canal de Reporte de Problemas no Mobile:**
  * `lib/views/lesson_detail_screen.dart` e `dictionary_screen.dart`: Botão de bandeira (`Icons.flag_outlined`) integrado ao modal `_showReportDialog`. Gravação assíncrona na tabela `reports` do Supabase para auditoria dos professores no Web Dashboard.
* **[US25] Persistência Offline Local com SQLite:**
  * `lib/helpers/database_helper.dart`: Implementação do banco local `sinaliza.db` com tabelas `users`, `lessons` e `progress` para leitura e escrita offline e sincronização posterior.
* **[US26] Autenticação Social via OAuth e Gestão Segura de Senhas:**
  * `lib/views/change_password_screen.dart` e `update_password_screen.dart`: Telas dedicadas para troca e confirmação criptografada de senha com Supabase Auth. Suporte a login rápido com Google OAuth (`OAuthProvider.google`).
* **[US27] Visualizador de Histórico de Versões (Changelog):**
  * `lib/views/changelog_screen.dart`: Tela informativa com histórico cronológico de lançamentos e notas de versão do aplicativo.

---

### B. Repositório: `sinaliza_web_dashboard` (Portal Web)
Aplicação desenvolvida do zero para controle administrativo e pedagógico:

* **[US28] Painel Analítico Geral (`src/pages/Dashboard.jsx`):**
  * Gráficos responsivos em tempo real com **Recharts** exibindo volume de alunos ativos, taxas de conclusão de módulos pedagógicos, média de XP e retenção da plataforma conectada diretamente ao Supabase PostgreSQL.
* **[US29] Gerenciador de Usuários e Permissões (`src/pages/CommunityManager.jsx` & `UsersList.jsx`):**
  * Tabela paginada com busca textual, toggle dinâmico de privilégios (`is_admin`) e integração com RPC seguro (`delete_user_account`) para banimento de contas infratoras.
* **[US30] & [US32] Gestão de Conteúdo e Sistema de Rascunhos (`src/pages/ContentManager.jsx`):**
  * Interface CRUD para criação, edição e exclusão de módulos e lições de LIBRAS.
  * **Sistema de Rascunhos (`is_draft`):** Switch visual animado que permite aos professores salvar lições em estado de rascunho sem que sejam exibidas precocemente aos alunos no app. Badges visuais destacando itens como "Rascunho" (âmbar) e "Publicado" (verde).
* **[US31] Central de Moderação de Reports (`src/pages/CommunityManager.jsx` - Aba Reports):**
  * Caixa de entrada de denúncias e relatos de erros enviados pelos alunos no mobile.
  * Visualização de tipo do alvo (`lesson` ou `dictionary`), autor e descrição da falha, com função de resolução (`handleResolveReport`) que atualiza o status para `resolved` no banco.
* **[US33] Model Tester Web / Laboratório de IA (`src/pages/ModelTester.jsx`):**
  * Ambiente de testes client-side rodando via **ONNX Runtime WebAssembly (Wasm)** e **MediaPipe Holistic** a 60 FPS.
  * Permite aos professores apontar a webcam e validar os modelos de visão V2 localmente no navegador, exibindo barras dinâmicas de probabilidade por classe sem precisar de ambiente Python instalado.
* **Autenticação Administrativa e Segurança (`src/pages/Login.jsx`, `ResetPassword.jsx`, `AuthContext.jsx`):**
  * Bloqueio estrito de acesso para usuários que não possuem flag `is_admin`, proteção de rotas privadas e fluxo de redefinição de credenciais.

---

### C. Repositório: `sinaliza_vision_backend` (API Server & Banco de Dados)
Infraestrutura de suporte desenvolvida no diretório `api_server/`:

* **API REST em Node.js / Express:**
  * Desenvolvimento de controladores e rotas REST para sincronização de progresso dos alunos (`/progress/quiz` e `/progress/challenge`), favoritos e listagens de módulos.
* **Migrações de Banco de Dados SQL V2 (`setup_db.sql` e scripts de migração):**
  * Criação da tabela `reports` com chaves estrangeiras para usuários e alvos (lições/dicionário).
  * Criação de colunas `is_draft` nas tabelas de módulos e lições.
  * Implementação de políticas de segurança **Row Level Security (RLS)** no PostgreSQL, garantindo que alunos só alterem seus próprios dados e que rotas administrativas exijam `is_admin = true`.

---

## 📂 4. Mapeamento de Artefatos de Código Produzidos por Arquivo

| Repositório | Arquivo Principal | Descrição da Implementação |
| :--- | :--- | :--- |
| `sinaliza_app_libras` | `lib/views/lesson_list_screen.dart` | Card do Desafio Final de Módulo ("Boss"), bloqueio, sorteio aleatório de sinais e badge "Módulo Dominado". |
| `sinaliza_app_libras` | `lib/views/challenge_sequence_screen.dart` | Execução do desafio sequencial na câmera com validação e pontuação. |
| `sinaliza_app_libras` | `lib/services/libras_inference_service.dart` | Motor de inferência local ONNX Runtime On-Device (~4ms). |
| `sinaliza_app_libras` | `lib/services/vision_extractor_service.dart` | Extração de pose e mãos a 30 FPS com Dart Isolates e Google ML Kit. |
| `sinaliza_app_libras` | `lib/views/theoretical_quiz_screen.dart` | Tela do Quiz Teórico com validação e desacoplamento do desafio prático. |
| `sinaliza_app_libras` | `lib/views/lesson_detail_screen.dart` | Detalhes da lição com integração do botão de envio de reports. |
| `sinaliza_app_libras` | `lib/views/change_password_screen.dart` | Fluxo seguro de redefinição de senha com Supabase. |
| `sinaliza_app_libras` | `lib/views/changelog_screen.dart` | Tela de notas de versão e atualizações do sistema. |
| `sinaliza_app_libras` | `lib/helpers/database_helper.dart` | Persistência local em SQLite (`sinaliza.db`) para suporte offline. |
| `sinaliza_web_dashboard` | `src/pages/Dashboard.jsx` | Painel analítico com gráficos Recharts e métricas do Supabase. |
| `sinaliza_web_dashboard` | `src/pages/CommunityManager.jsx` | Gestão de alunos, alternância de permissão ADM e Caixa de Entrada de Reports. |
| `sinaliza_web_dashboard` | `src/pages/ContentManager.jsx` | CRUD de módulos e lições com sistema de rascunhos (`is_draft`). |
| `sinaliza_web_dashboard` | `src/pages/ModelTester.jsx` | Laboratório de testes de IA em WebAssembly a 60 FPS na webcam. |
| `sinaliza_web_dashboard` | `src/context/AuthContext.jsx` | Contexto de autenticação e proteção de rotas administrativas. |
| `sinaliza_web_dashboard` | `src/pages/Login.jsx` / `ResetPassword.jsx` | Autenticação restrita para administradores e recuperação de senha. |
| `sinaliza_vision_backend` | `api_server/` | Servidor Node.js/Express com rotas de progresso desacoplado e API REST. |
| `sinaliza_vision_backend` | `scripts/setup_db.sql` | Scripts de migração com tabela `reports`, campo `is_draft` e RLS. |

---

## 🏆 5. Resumo das Métricas e Resultados Técnicos Obtidos

* **Gamificação Avançada e Retenção:** Implementação do conceito de "Boss Challenge" em cada módulo, exigindo 100% de conclusão prévia das lições para consolidar o aprendizado prático antes de liberar o selo "Módulo Dominado".
* **100% On-Device no Mobile:** A inferência passou de chamadas de rede dependentes de servidor para execução local em **~4 ms** via processador do smartphone.
* **Plataforma Web Completa:** Dashboard administrativo entregue e funcional, permitindo controle pedagógico (conteúdos e rascunhos), moderação de problemas e validação instantânea de IA no browser a 60 FPS.
* **Inclusão e Acessibilidade:** Suporte técnico para usuários destros e canhotos e eliminação de distorção de enquadramento da câmera.
* **Integridade de Dados:** Banco local SQLite garantindo funcionamento do aplicativo mesmo sem internet e sincronização com PostgreSQL/Supabase via RLS.
