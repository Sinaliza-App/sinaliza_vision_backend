# 🤝 Guia de Integração e MLOps — Sinaliza App
> **Para:** Khalil & Equipe de Desenvolvimento do Sinaliza  
> **Assunto:** Novos Módulos de Visão Computacional, Estúdio de Coleta Web e Curadoria Contínua  

---

## 👋 Olá, Khalil!

Ao dar `git pull` neste repositório, você notará a adição de novas funcionalidades focadas no **pipeline de Visão Computacional, Coleta de Dados Web e Aprendizado Contínuo (MLOps)** do **Sinaliza App**.

Este documento foi criado para esclarecer exatamente o que foi implementado, garantir que **nenhum trabalho seu anterior foi afetado ou alterado**, e mostrar como você pode interagir com esses novos recursos se desejar.

---

## 🛡️ 1. Garantia de Não-Interferência (O que NÃO mudou)

1. **Suas tabelas no Supabase continuam intactas:**
   * Nenhuma tabela existente (`users`, `favorite_signs`, `quiz_progress`, etc.) foi alterada ou excluída.
2. **Sua autenticação e permissões continuam idênticas:**
   * O `AuthContext.jsx` e o fluxo de login via Supabase continuam operando normalmente (`is_admin: true` para professores/admins, `is_admin: false` para alunos).
3. **O servidor Node.js (`api_server/`) segue intocado:**
   * Seu backend Node.js / Express continua rodando de forma 100% independente.

---

## 🚀 2. O que foi adicionado ao projeto?

### A. 🎥 Estúdio de Coleta Web (`/dashboard/data-studio`)
* **Objetivo:** Permitir que professores e alunos gravem amostras de Libras direto pelo navegador Google Chrome/Edge com webcam, **sem precisar instalar Python, OpenCV ou PyTorch no computador**.
* **Tecnologia:** Utiliza o **MediaPipe Holistic (WebAssembly)** diretamente no client-side para rastrear 258 pontos corporais (Pose + Mão Esquerda + Mão Direita) a 60 FPS.
* **Segurança de Dados:** Salva arquivos `.npy` **brutos** (sem normalização prematura) na pasta de dataset para que o PyTorch possa treinar a rede neural LSTM.

### B. 🛡️ Central de Curadoria e Promoção de Dataset (`/dashboard/curator`)
* **Objetivo:** Permitir aos professores aprovar, corrigir o rótulo ou descartar amostras enviadas por alunos no app.
* **Promoção com 1 Clique:** Botão *"Promover Dataset"* que consolida as amostras aprovadas na pasta oficial `dataset/treinamento/v2/` e gera o `CHANGELOG.md` automaticamente.

### C. 🧪 Laboratório de IA Web (`/dashboard/ai-lab`)
* **Objetivo:** Testar em tempo real se o modelo de IA (MLP do Alfabeto e LSTM de Sinais Dinâmicos) está reconhecendo os gestos na webcam direto pelo navegador via **ONNX Runtime Web (WebAssembly)**.

---

## 🗄️ 3. Como funciona a conexão com o Banco de Dados

Para evitar sobrecarregar o limite gratuito do Supabase ou gastar espaço de banco desnecessariamente:

```
┌────────────────────────────────────────────────────────┐
│         SUPABASE / POSTGRESQL (Nuvem Compartilhada)     │
│                                                        │
│  Tabela: `feedback_samples`                            │
│  ├── id, user_id (FK -> users.id)                      │
│  ├── predicted_class, corrected_class                  │
│  ├── mode, version, status, reporter_role              │
│  └── raw_file_path (apenas o caminho em texto)         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            DISCO LOCAL / STORAGE DE ARQUIVOS           │
│                                                        │
│  Arquivos binários `.npy` (30x258 floats ~31 KB cada)  │
│  salvos em `dataset/feedback/` e `dataset/treinamento/`│
└────────────────────────────────────────────────────────┘
```

* **Conexão Híbrida Inteligente:** O backend Python (`feedback_api.py`) lê a variável `DATABASE_URL` do `.env`. Se configurado com o PostgreSQL do Supabase, grava lá. Se estiver rodando offline/sem conexão, usa o SQLite local (`sinaliza_feedback.db`) sem quebrar nada.

---

## 📡 4. Endpoints da API de Visão (FastAPI - Porta 8000)

Caso queira integrar funcionalidades do Mobile ou do seu painel no futuro, aqui estão as rotas disponíveis:

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/classes` | Lista dinâmica de todos os sinais suportados e status de treino. |
| `POST` | `/api/classes` | Cadastra um novo sinal no catálogo (Apenas professores). |
| `POST` | `/coleta/amostra` | Recebe matriz de keypoints gravada e registra no banco. |
| `GET` | `/feedback/pendentes` | Retorna a fila de amostras enviadas por alunos para curadoria. |
| `POST` | `/feedback/avaliar` | Aprova ou rejeita uma amostra pendente. |
| `POST` | `/feedback/promover` | Promove amostras validadas para a nova versão do dataset (`v2`). |
| `GET` | `/feedback/exportar-csv` | Download do arquivo CSV com todas as amostras registradas. |

---

## 💻 5. Como rodar o projeto completo localmente

### 1. Iniciar o Frontend Web (Dashboard):
```bash
cd sinaliza_web_dashboard
npm run dev
# Acesse em: http://localhost:5173
```

### 2. Iniciar a API de Feedback e Coleta (Python):
```bash
# Na raiz do repositório
uvicorn src.feedback_loop.feedback_api:app --host 0.0.0.0 --port 8000 --reload
# Documentação Swagger interativa em: http://localhost:8000/docs
```

---

## 🎁 6. Oportunidade de Gamificação no Mobile (Ideia para você!)

Como a rota `POST /coleta/amostra` já retorna um campo `"xp_reward": 10`, você pode adicionar uma tela no app Flutter de *"Desafio de Coleta"* onde o aluno grava um sinal na câmera do celular e ganha **+10 XP** no `total_score` dele no Supabase!

Qualquer dúvida, estamos 100% à disposição! 🚀
