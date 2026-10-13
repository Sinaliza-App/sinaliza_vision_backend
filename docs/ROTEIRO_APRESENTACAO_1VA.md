# 🎬 ROTEIRO DE VÍDEO DEMONSTRATIVO — 1ª AVALIAÇÃO (2026.2)
**Projeto:** Plataforma SINALIZA  
**Disciplina:** PIEC-3 — Projeto Integrado de Engenharia de Computação 3  
**Professor:** Waldemar Pires Ferreira Neto  
**Equipe:** Emanuel Khalil Fernandes Novaes Angelim & Luiz Henrique Padilha Cavalcante  
**Escopo do Vídeo:** Exclusivamente as funcionalidades e modelos desenvolvidos na 1ª VA (2026.2)  
**Duração Alvo:** ~04:45 min (Segmento Único Dinâmico | Método de Coluna Única com Inserções)  

---

### ⏱️ BLOCO 1: INTRODUÇÃO & ESCOPO EXCLUSIVO DA 1ª VA (00:00 – 00:35)

[CENA: Câmera com os apresentadores Emanuel Khalil e Luiz Henrique lado a lado.]

[TEXTO NA TELA: "SINALIZA — Demonstração das Funcionalidades da 1ª VA (2026.2)"]  
[TEXTO NA TELA: "Foco Exclusivo nas Entregas do Semestre: Web Dashboard, Edge AI On-Device & IA V2"]

[ORADOR: Emanuel Khalil]  
"Olá, professor Waldemar! Este vídeo é dedicado exclusivamente à demonstração prática das funcionalidades desenvolvidas e entregues na 1ª VA de PIEC-3. Não apresentaremos recursos herdados de semestres anteriores, focando 100% nas inovações desta etapa: a criação completa do nosso Web Dashboard administrativo, o desacoplamento das novas avaliações no mobile, a nova inferência de Visão Computacional On-Device e os dois novos modelos neurais da V2."

[ORADOR: Luiz Henrique]  
"Iniciaremos demonstrando a engenharia dos novos modelos de inteligência artificial da V2 e a normalização geométrica de coordenadas desenvolvida neste período."

---

### ⏱️ BLOCO 2: INTELIGÊNCIA ARTIFICIAL V2 & ENGENHARIA DE KEYPOINTS (00:35 – 01:45)

[INSERÇÃO VISUAL: Gravação de tela do terminal e do ambiente de validação. Exibição da extração do MediaPipe Holistic com o esqueleto de 258 pontos anatômicos sobreposto à captura de vídeo.]

[TEXTO NA TELA: "IA V2: Transição de YOLO para 258 Keypoints Anatômicos"]  
[TEXTO NA TELA: "Normalização Relativa: Centralização nos Ombros e Punhos (Invariância de Escala)"]

[ORADOR: Luiz Henrique]  
"Na 1ª VA, descontinuamos totalmente o modelo anterior baseado em YOLO e desenvolvemos um pipeline baseado em 258 pontos anatômicos. O primeiro diferencial implementado foi a normalização geométrica relativa: centralizamos os pontos corporais no ponto médio dos ombros e as mãos no punho, dividindo pela distância intercostal. Isso eliminou distorções por enquadramento ou distância da câmera."

[INSERÇÃO VISUAL: Exibição dos scripts de validação (`testar_lstm.py` / `exportar_onnx.py`), gráficos de perda/acurácia da V2 e matriz de confusão.]

[TEXTO NA TELA: "Novos Modelos V2 Concluídos na 1ª VA:"]  
[TEXTO NA TELA: "• MLP Alfabeto (US18): 27 Classes (A-Z + Ç) | >95% Acurácia | 169.6 KB"]  
[TEXTO NA TELA: "• LSTM Dinâmica (US15): 31 Classes | 98.92% Acurácia Validação | 1.37 MB"]  
[TEXTO NA TELA: "• Exportação ONNX Universal: Validação Numérica Δ < 10⁻⁴ | Latência ~4ms"]

[ORADOR: Luiz Henrique]  
"Treinamos e finalizamos os dois novos modelos oficiais da V2: a rede densa MLP para o alfabeto de 27 classes com acurácia acima de 95%, e a rede temporal LSTM para 31 expressões dinâmicas, alcançando 98.92% de acurácia de validação com 30 frames de janela temporal. Ambos foram convertidos para o formato universal ONNX, com divergência numérica imperceptível e tamanho ultraleve de apenas 1,5 MB somados."

---

### ⏱️ BLOCO 3: NOVO PORTAL WEB DE GESTÃO & MODEL TESTER WEB (01:45 – 03:00)

[INSERÇÃO VISUAL: Compartilhamento de tela do Web Dashboard (`sinaliza_web_dashboard`), mostrando a tela inicial analítica com layout responsivo em tema escuro.]

[TEXTO NA TELA: "Web Dashboard (Criado do Zero na 1ª VA)"]  
[TEXTO NA TELA: "[US28] Painel Analítico Geral: Métricas com Recharts"]  
[TEXTO NA TELA: "[US29] Gestão de Usuários: Permissões e Row Level Security (RLS)"]

[ORADOR: Emanuel Khalil]  
"Todo o Web Dashboard foi concebido e implementado do zero nesta 1ª VA. Como novidade para os professores, implementamos na US28 o Painel Analítico Geral com a biblioteca Recharts, trazendo gráficos dinâmicos de engajamento, média de XP e retenção dos alunos direto do Supabase PostgreSQL. Na US29, criamos o Gerenciador de Usuários com busca paginada e alternância de privilégios de administrador em tempo real."

[INSERÇÃO VISUAL: Navegação para a tela de 'Gestão de Conteúdo' (`/modules`). Emanuel clica para criar uma lição, digita os dados e salva, mostrando a sincronização imediata.]

[TEXTO NA TELA: "[US30] Content Manager: CRUD de Módulos e Lições de LIBRAS"]

[ORADOR: Emanuel Khalil]  
"Na US30, entregamos o Content Manager, uma interface CRUD completa onde o corpo docente cria e edita módulos e lições de LIBRAS com status de publicação, alimentando diretamente o aplicativo móvel."

[INSERÇÃO VISUAL: Emanuel acessa a página do 'Model Tester' (`/dashboard/ai-lab`). A webcam liga no navegador, o MediaPipe rastreia os pontos a 60 FPS e barras de progresso ao vivo exibem a classificação instantânea.]

[TEXTO NA TELA: "[US31] Model Tester Web: IA On-Device via WebAssembly (60 FPS)"]  
[TEXTO NA TELA: "Zero-Setup: Execução dos modelos ONNX no navegador sem Python"]

[ORADOR: Emanuel Khalil]  
"E o módulo mais inovador do Dashboard entregue na última sprint foi o Model Tester (US31). Criamos um laboratório de IA que roda direto no navegador usando ONNX Runtime WebAssembly e MediaPipe Holistic. O professor pode testar os novos modelos V2 que o Luiz gerou diretamente pela webcam a 60 FPS, com visualização das probabilidades por classe e sem precisar instalar Python ou dependências na máquina."

---

### ⏱️ BLOCO 4: APP MOBILE — DESACOPLAMENTO, OFFLINE E EDGE AI (03:00 – 04:20)

[INSERÇÃO VISUAL: Espelhamento de tela do aplicativo Flutter (`sinaliza_app_libras`) em execução no smartphone.]

[TEXTO NA TELA: "Novas Funcionalidades Mobile (1ª VA):"]  
[TEXTO NA TELA: "[US26] Autenticação Social via OAuth & Telas Seguras de Troca de Senha"]  
[TEXTO NA TELA: "[US27] Visualizador de Changelog / Notas de Atualização"]  
[TEXTO NA TELA: "[US25] Persistência Offline Local com SQLite (sinaliza.db)"]

[ORADOR: Emanuel Khalil]  
"No aplicativo móvel, implementamos nesta 1ª VA a autenticação social via OAuth na US26, com telas dedicadas e seguras para redefinição de senha; na US27 criamos a tela de Changelog; e na US25 adicionamos o suporte à persistência offline com SQLite local através da classe DatabaseHelper."

[INSERÇÃO VISUAL: Emanuel entra na trilha pedagógica e demonstra a realização do Quiz Teórico (US24). As alternativas são embaralhadas e validadas imediatamente. Em seguida, mostra que o Desafio Prático (US22/US23) permanece disponível de forma independente.]

[TEXTO NA TELA: "[US22] Desacoplamento Total: Quiz Teórico vs. Desafio Prático"]  
[TEXTO NA TELA: "[US24] Quiz Teórico: Validação Conceitual Imediata"]  
[TEXTO NA TELA: "[US23] Desafio Prático: Sequência de Sinais em Tempo Real"]

[ORADOR: Emanuel Khalil]  
"Um avanço arquitetural desta VA foi o desacoplamento total entre Quiz Teórico e Desafio Prático (US22). Criamos fluxos e endpoints distintos no backend: o aluno realiza o Quiz Teórico com perguntas conceituais e embaralhamento na US24, e o Desafio Prático continua pendente de forma isolada, registrando pontuações sem sobrescrever dados."

[INSERÇÃO VISUAL: Emanuel inicia o 'Desafio Prático'. A câmera frontal do celular ativa. O esqueleto é detectado a 30 FPS sem travamento de tela. Emanuel executa a letra 'A' e depois uma expressão contínua. O app reconhece em milissegundos e exibe a barra neon de acerto.]

[TEXTO NA TELA: "Nova Visão On-Device (Sprint 3 / 1ª VA):"]  
[TEXTO NA TELA: "[US17] Inferência On-Device 100% Offline (ONNX Runtime ~4ms)"]  
[TEXTO NA TELA: "[US19] Correção de Aspect Ratio da Câmera (3:4 vs 4:3)"]  
[TEXTO NA TELA: "[US20] Algoritmo Dual-Candidate (Suporte a Destros e Canhotos)"]  
[TEXTO NA TELA: "[US21] Extração Híbrida Assíncrona via Dart Isolates (30 FPS)"]

[ORADOR: Emanuel Khalil]  
"E na Sprint 3, realizamos a integração da Nova Visão Computacional On-Device no app:
1. Na US17, a inferência passou a rodar localmente pelo processador do smartphone via ONNX Runtime e Dart Isolates a 30 FPS sem travar a interface (US21), atingindo uma latência de apenas 4 milissegundos, 100% offline.
2. Na US19, aplicamos a correção matemática de escalonamento anisotrópico nos eixos X, Y e Z, eliminando o achatamento da imagem da câmera vertical do celular.
3. Na US20, implementamos o Algoritmo Dual-Candidate, que avalia automaticamente os dois arranjos de mãos e garante precisão idêntica tanto para alunos destros quanto para canhotos."

---

### ⏱️ BLOCO 5: CONCLUSÃO & RESULTADOS OBTIDOS (04:20 – 04:45)

[CENA: Retorno para a câmera principal com Emanuel e Luiz.]

[TEXTO NA TELA: "Resultados Obtidos na 1ª VA:"]  
[TEXTO NA TELA: "✓ Web Dashboard Completo em Produção"]  
[TEXTO NA TELA: "✓ Model Tester Web com IA em WebAssembly (60 FPS)"]  
[TEXTO NA TELA: "✓ Visão On-Device no Mobile a 4ms (Offline, Invariante e Inclusiva)"]  
[TEXTO NA TELA: "✓ Modelos V2: MLP 27 classes (>95%) e LSTM 31 classes (98.92%)"]

[ORADOR: Luiz Henrique]  
"Evidenciamos que todas as funcionalidades planejadas para a 1ª VA foram concluídas com êxito, entregando modelos leves e acurados integrados à arquitetura global."

[ORADOR: Emanuel Khalil]  
"E com o Web Dashboard e o aplicativo mobile comunicando-se perfeitamente, o SINALIZA atinge um patamar profissional de engenharia, pronto para a 2ª VA. Muito obrigado pela atenção!"

[INSERÇÃO VISUAL: Tela final de encerramento com títulos dos integrantes e referências às US implementadas na 1ª VA.]
