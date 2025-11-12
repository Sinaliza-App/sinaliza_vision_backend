// Importa o 'dotenv' primeiro para carregar o .env (necessário para o JWT_SECRET)
require('dotenv').config(); 

// --- Imports das Bibliotecas ---
const express = require('express');
const cors = require('cors');
const bcrypt = require('bcryptjs'); // Para hashear senhas
const jwt = require('jsonwebtoken'); // Para gerar tokens de login
const authMiddleware = require('./authMiddleware'); // Nosso "segurança"
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

app.post('/progress', authMiddleware, async (req, res) => {
  // O authMiddleware nos dá o 'req.user' com o ID do usuário logado
  const userId = req.user.id;
  
  // O Flutter deve enviar o ID da lição no corpo da requisição
  const { lesson_id } = req.body;

  if (!lesson_id) {
    return res.status(400).json({ message: 'O ID da lição (lesson_id) é obrigatório.' });
  }

  console.log(`Usuário (ID: ${userId}) está salvando progresso para a lição (ID: ${lesson_id}).`);

  try {
    const client = await pool.connect();
    try {
      // Insere o novo registro de progresso
      const result = await client.query(
        'INSERT INTO progress (user_id, lesson_id) VALUES ($1, $2) RETURNING id',
        [userId, lesson_id]
      );
      
      res.status(201).json({ 
        message: 'Progresso salvo com sucesso!', 
        progressId: result.rows[0].id 
      });

    } catch (dbError) {
      // 500: Erro geral do servidor
      let statusCode = 500;
      let errorMessage = 'Erro ao salvar progresso.';

      // 23505 é o código de erro do PostgreSQL para "violão de restrição UNIQUE"
      // (a que criamos: user_lesson_unique)
      if (dbError.code === '23505') {
        statusCode = 409; // 409 = Conflict
        errorMessage = 'Este progresso já foi salvo anteriormente.';
      } else {
        console.error('Erro no banco de dados:', dbError);
      }
      
      res.status(statusCode).json({ message: errorMessage });
    } finally {
      client.release();
    }
    
  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});
app.get('/progress', authMiddleware, async (req, res) => {
  // O authMiddleware nos dá o 'req.user' com o ID do usuário logado
  const userId = req.user.id;

  console.log(`Usuário (ID: ${userId}) está buscando seu progresso.`);

  try {
    const client = await pool.connect();
    try {
      // Busca todos os registros de progresso para este usuário
      const result = await client.query(
        'SELECT * FROM progress WHERE user_id = $1',
        [userId]
      );
      
      // Retorna a lista de registros de progresso como um JSON
      // O app Flutter usará isso para ver quais 'lesson_id's já foram completados
      res.status(200).json(result.rows);

    } catch (dbError) {
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao buscar progresso.' });
    } finally {
      client.release();
    }
    
  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

// --- Rotas da API ---

/**
 * Rota de Teste (GET /)
 * Verifica se a API está online.
 */
app.get('/', (req, res) => {
  res.send('A API de Usuários (Node.js) do Sinaliza está funcionando!');
});

/**
 * Rota Protegida (GET /users/me)
 * Busca os dados do usuário logado.
 */
app.get('/users/me', authMiddleware, async (req, res) => {
  try {
    const userId = req.user.id;
    const client = await pool.connect();
    try {
      const result = await client.query('SELECT id, name, email, created_at FROM users WHERE id = $1', [userId]);
      if (result.rows.length === 0) {
        return res.status(404).json({ message: 'Usuário não encontrado.' });
      }
      res.status(200).json(result.rows[0]);
    } catch (dbError) {
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao buscar usuário.' });
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

/**
 * ==================================================================
 * Rota Protegida (GET /lessons) - O NOVO CÓDIGO DO PASSO 2
 * Busca todas as lições cadastradas no banco de dados.
 * ==================================================================
 */
app.get('/lessons', authMiddleware, async (req, res) => {
  // O authMiddleware já validou o token e nos deu o req.user
  console.log(`Usuário (ID: ${req.user.id}) está buscando as lições.`);

  try {
    const client = await pool.connect();
    try {
      // Busca todas as lições, ordenadas pelo ID
      const result = await client.query('SELECT * FROM lessons ORDER BY id ASC');
      
      // Retorna a lista de lições como um JSON
      res.status(200).json(result.rows);

    } catch (dbError) {
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao buscar lições.' });
    } finally {
      client.release();
    }
    
  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
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