# 🐳 Guia de Execução com Docker - Plataforma Sinaliza

Este guia explica como executar o ecossistema **Sinaliza** de forma 100% unificada com Docker, permitindo que qualquer desenvolvedor, avaliador ou professor execute o projeto **sem precisar instalar Node.js, Python, PostgreSQL, Flutter ou Android Studio manualmente no computador**.

---

## 🚀 Como Iniciar Tudo com 1 Único Comando

### Pré-requisito
* Apenas o [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e em execução na máquina.

### Execução
Na raiz do projeto (`c:/Projetos/SINALIZA`), abra o terminal e execute:

```bash
docker compose up --build
```

O Docker fará o download das imagens, instalará todas as dependências isoladamente e iniciará os serviços.

---

## 🌐 Serviços Disponíveis

Assim que os containers subirem, os seguintes serviços estarão disponíveis:

| Serviço | URL | Descrição |
| :--- | :--- | :--- |
| **Dashboard Web** | [http://localhost:5173](http://localhost:5173) | Painel educacional e administrativo (React + Vite) |
| **API Backend Node** | [http://localhost:3000](http://localhost:3000) | API de usuários, progresso, ranking e autenticação |
| **Documentação Swagger** | [http://localhost:3000/api-docs](http://localhost:3000/api-docs) | Documentação interativa de todos os endpoints REST |
| **API Visão & Feedback** | [http://localhost:8000/docs](http://localhost:8000/docs) | Microserviço em Python (FastAPI) para dados de IA |

---

## 📱 E o Aplicativo Mobile (Flutter)?

Uma das dúvidas mais comuns é: ***"O professor ou avaliador precisa instalar Flutter, Dart, Android Studio e Android SDK para rodar o app?"***

###  Resposta: NÃO! Ninguém precisa instalar nada disso para testar.
* **Apps mobile compilam para um arquivo executável nativo (`.apk`).**
* O instalador já está pronto e disponível em:
  ```text
  sinaliza_web_dashboard/public/downloads/sinaliza.apk
  ```
* **Como testar:**
  1. **Direto no Celular:** O professor pode acessar o Dashboard Web no navegador do celular ou PC, clicar em **"Baixar o App"** ou ler o QR Code e instalar direto no Android.
  2. **No Computador:** Basta arrastar o arquivo `sinaliza.apk` para qualquer emulador Android leve (como BlueStacks, NoxPlayer, LDPlayer ou o próprio emulador do Android Studio, caso já possua).

---

### 🛠️ E se alguém quiser COMPILAR o código-fonte do App via Docker?
Caso alguém queira alterar o código Dart e compilar um novo APK sem ter Flutter nem Android Studio instalados no Windows, criamos o arquivo `sinaliza_app_libras/Dockerfile.build`.

Para compilar o APK via Docker:
```bash
cd sinaliza_app_libras
docker build -f Dockerfile.build -t sinaliza-builder .
docker run --rm -v "${PWD}/build/app/outputs/flutter-apk:/app/build/app/outputs/flutter-apk" sinaliza-builder
```
O container executará o build oficial do Flutter com Java e Android SDK embutidos e salvará o `.apk` pronto na pasta `build/app/outputs/flutter-apk`.

---

## 🛑 Como Parar os Serviços

Para encerrar todos os containers e liberar as portas:

```bash
docker compose down
```
