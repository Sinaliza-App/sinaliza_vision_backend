# ==========================================
# Dockerfile: API Backend Node.js (Express)
# ==========================================
FROM node:20-alpine

# Cria diretório de trabalho
WORKDIR /app

# Copia manifestos de dependências
COPY package*.json ./

# Instala dependências do projeto
RUN npm install

# Copia o restante do código da API
COPY . .

# Expõe a porta padrão da API
EXPOSE 3000

# Variáveis padrão (podem ser sobrescritas pelo compose ou .env)
ENV PORT=3000
ENV NODE_ENV=production

# Comando de inicialização
CMD ["node", "index.js"]
