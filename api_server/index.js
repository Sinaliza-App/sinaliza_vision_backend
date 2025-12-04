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

// --- Configuração do Banco de Dados ---
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

app.get('/', (req, res) => {
  res.send('A API de Usuários (Node.js) do Sinaliza está funcionando!');
});

// --- NOVA ROTA: LISTAR MÓDULOS ---
app.get('/modules', authMiddleware, async (req, res) => {
  const userId = req.user.id;

  try {
    const client = await pool.connect();
    try {
      // Query poderosa: Conta lições totais e lições feitas POR MÓDULO
      const result = await client.query(`
        SELECT 
          m.id, 
          m.title, 
          m.description, 
          m.icon_name,
          COUNT(l.id)::int as total_lessons,
          COUNT(p.id)::int as completed_lessons
        FROM modules m
        LEFT JOIN lessons l ON m.id = l.module_id
        LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = $1
        GROUP BY m.id
        ORDER BY m.id ASC
      `, [userId]);
      
      // O frontend vai receber algo como:
      // { id: 1, title: "Alfabeto", total_lessons: 26, completed_lessons: 5 }
      
      res.status(200).json(result.rows);

    } catch (dbError) {
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao buscar módulos.' });
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro geral:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

// --- ROTA ATUALIZADA: LISTAR LIÇÕES (COM FILTRO) ---
app.get('/lessons', authMiddleware, async (req, res) => {
  const { module_id } = req.query; // Lê o ?module_id=1 da URL

  try {
    const client = await pool.connect();
    try {
      let query = 'SELECT * FROM lessons';
      let params = [];

      if (module_id) {
        query += ' WHERE module_id = $1';
        params.push(module_id);
      }

      query += ' ORDER BY id ASC';

      const result = await client.query(query, params);
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

// --- Rota de Perfil com Pontuação ---
app.get('/users/me', authMiddleware, async (req, res) => {
  try {
    const userId = req.user.id;
    const client = await pool.connect();
    try {
      const result = await client.query(`
        SELECT 
          u.id, u.name, u.email, u.created_at,
          COALESCE(SUM(p.score), 0) as total_score
        FROM users u
        LEFT JOIN progress p ON u.id = p.user_id
        WHERE u.id = $1
        GROUP BY u.id, u.name, u.email, u.created_at
      `, [userId]);

      if (result.rows.length === 0) {
        return res.status(404).json({ message: 'Usuário não encontrado.' });
      }

      const user = result.rows[0];
      user.total_score = parseInt(user.total_score); // Garante número

      res.status(200).json(user);

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

// --- Rota de Progresso (Leitura) ---
app.get('/progress', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  try {
    const client = await pool.connect();
    try {
      const result = await client.query('SELECT * FROM progress WHERE user_id = $1', [userId]);
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

// --- Rota de Progresso (Escrita) ---
app.post('/progress', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  const { lesson_id, score } = req.body;

  if (!lesson_id) {
    return res.status(400).json({ message: 'O ID da lição (lesson_id) é obrigatório.' });
  }

  const finalScore = score || 10;
  let client;

  try {
    client = await pool.connect();
    
    const result = await client.query(
      'INSERT INTO progress (user_id, lesson_id, score) VALUES ($1, $2, $3) RETURNING id',
      [userId, lesson_id, finalScore]
    );
    
    return res.status(201).json({ 
      message: `Progresso salvo! Você ganhou ${finalScore} pontos!`, 
      progressId: result.rows[0].id 
    });

  } catch (error) {
    if (error.code === '23505') {
      return res.status(409).json({ message: 'Este progresso já foi salvo anteriormente.' });
    }
    console.error('Erro na rota /progress:', error);
    if (!res.headersSent) {
      return res.status(500).json({ message: 'Erro ao salvar progresso.' });
    }
  } finally {
    if (client) {
      client.release();
    }
  }
});

// --- Rota de Cadastro ---
app.post('/users/register', async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ message: 'Nome, e-mail e senha são obrigatórios.' });
    }

    // Aqui você pode adicionar a validação de senha forte se quiser

    const salt = await bcrypt.genSalt(10);
    const passwordHash = await bcrypt.hash(password, salt);

    const client = await pool.connect();
    try {
      // Verifica email
      const emailCheck = await client.query('SELECT * FROM users WHERE email = $1', [email]);
      if (emailCheck.rows.length > 0) {
        return res.status(409).json({ message: 'Este e-mail já está em uso.' });
      }
      
      // Verifica nome
      const nameCheck = await client.query('SELECT * FROM users WHERE name = $1', [name]);
      if (nameCheck.rows.length > 0) {
        return res.status(409).json({ message: 'Este nome de usuário já está em uso.' });
      }

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
      if (dbError.code === '23505') {
         if (dbError.constraint === 'users_email_key') return res.status(409).json({ message: 'Este e-mail já está em uso.' });
         if (dbError.constraint === 'users_name_unique') return res.status(409).json({ message: 'Este nome de usuário já está em uso.' });
      }
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao salvar usuário no banco.' });
    } finally {
      client.release();
    }
    
  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

// --- Rota de Login ---
app.post('/users/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ message: 'E-mail e senha são obrigatórios.' });
    }

    const client = await pool.connect();
    try {
      const result = await client.query('SELECT * FROM users WHERE email = $1', [email]);
      
      if (result.rows.length === 0) {
        return res.status(401).json({ message: 'E-mail ou senha inválidos.' });
      }

      const user = result.rows[0];
      const isPasswordCorrect = await bcrypt.compare(password, user.password_hash);

      if (!isPasswordCorrect) {
        return res.status(401).json({ message: 'E-mail ou senha inválidos.' });
      }

      const payload = {
        id: user.id,
        email: user.email,
      };
      
      const token = jwt.sign(
        payload, 
        process.env.JWT_SECRET, 
        { expiresIn: '1d' }
      );

      res.status(200).json({
        message: 'Login bem-sucedido!',
        token: token,
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