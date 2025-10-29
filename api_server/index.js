// Importa o 'dotenv' primeiro para carregar o .env (necessário para o JWT_SECRET)
require('dotenv').config(); 

// --- Imports das Bibliotecas ---
const express = require('express');
const cors = require('cors');
const bcrypt = require('bcryptjs'); // Para hashear senhas
const jwt = require('jsonwebtoken'); // Para gerar tokens de login
const { Pool } = require('pg'); // Para o PostgreSQL

// --- Configuração da Aplicação ---
const app = express();
const port = 3000;

// --- Configuração do Banco de Dados (Usando a "Solução Cirúrgica" que funcionou) ---
const pool = new Pool({
  user: 'postgres',
  host: '127.0.0.1', // Usando 127.0.0.1 que resolveu o erro 'InitPostgres'
  database: 'sinaliza_db',
  password: 'Sinaliza282006#', // Sua senha confirmada
  port: 5432,
});

// --- Middlewares Essenciais ---
app.use(cors()); // Permite que o Flutter acesse a API
app.use(express.json()); // Permite que o servidor leia JSON no corpo das requisições

// --- Rotas da API ---

/**
 * Rota de Teste (GET /)
 * Verifica se a API está online.
 */
app.get('/', (req, res) => {
  res.send('A API de Usuários (Node.js) do Sinaliza está funcionando!');
});

/**
 * Rota de Cadastro de Usuário (POST /users/register)
 * Recebe nome, email e senha, salva no banco.
 */
app.post('/users/register', async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ message: 'Nome, e-mail e senha são obrigatórios.' });
    }

    // Criptografa a senha antes de salvar
    const salt = await bcrypt.genSalt(10);
    const passwordHash = await bcrypt.hash(password, salt);

    const client = await pool.connect();
    try {
      // Verifica se o email já existe
      const emailCheck = await client.query('SELECT * FROM users WHERE email = $1', [email]);
      if (emailCheck.rows.length > 0) {
        return res.status(409).json({ message: 'Este e-mail já está em uso.' }); // 409 = Conflict
      }

      // Insere o novo usuário
      const result = await client.query(
        'INSERT INTO users (name, email, password_hash) VALUES ($1, $2, $3) RETURNING id',
        [name, email, passwordHash]
      );
      
      const newUserId = result.rows[0].id;
      
      res.status(201).json({ 
        message: 'Usuário cadastrado com sucesso!', 
        userId: newUserId 
      });

    } catch (dbError) {
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao salvar usuário no banco.' });
    } finally {
      client.release(); // Libera a conexão
    }

  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

/**
 * Rota de Login de Usuário (POST /users/login)
 * Recebe email e senha, verifica e retorna um JWT se for válido.
 */
app.post('/users/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ message: 'E-mail e senha são obrigatórios.' });
    }

    const client = await pool.connect();
    try {
      // 1. Buscar o usuário pelo e-mail
      const result = await client.query('SELECT * FROM users WHERE email = $1', [email]);
      
      if (result.rows.length === 0) {
        // Usuário não encontrado
        return res.status(401).json({ message: 'E-mail ou senha inválidos.' }); // 401 Unauthorized
      }

      const user = result.rows[0];

      // 2. Comparar a senha enviada com o hash salvo no banco
      const isPasswordCorrect = await bcrypt.compare(password, user.password_hash);

      if (!isPasswordCorrect) {
        // Senha incorreta
        return res.status(401).json({ message: 'E-mail ou senha inválidos.' }); // 401 Unauthorized
      }

      // 3. SUCESSO! Gerar o Token JWT
      const payload = {
        id: user.id,
        email: user.email,
      };
      
      const token = jwt.sign(
        payload, 
        process.env.JWT_SECRET, // Lê o segredo do arquivo .env
        { expiresIn: '1d' } // Token expira em 1 dia
      );

      // 4. Enviar o token e os dados do usuário para o Flutter
      res.status(200).json({
        message: 'Login bem-sucedido!',
        token: token, // O crachá de acesso
        user: {
          id: user.id,
          name: user.name,
          email: user.email,
        },
      });

    } catch (dbError) {
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao tentar logar usuário.' });
    } finally {
      client.release();
    }

  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

// --- Iniciar o Servidor ---
app.listen(port, () => {
  console.log(`Servidor Node.js rodando na porta http://localhost:${port}`);
});