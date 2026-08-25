require('dotenv').config(); 

// --- Imports das Bibliotecas ---
const express = require('express');
const cors = require('cors');
const bcrypt = require('bcryptjs'); // Para hashear senhas
const jwt = require('jsonwebtoken'); // Para gerar tokens de login
const authMiddleware = require('./authMiddleware'); // Nosso "segurança"
const { Pool } = require('pg'); // Para o PostgreSQL
// --- 1. IMPORTAR O SWAGGER ---
const swaggerUi = require('swagger-ui-express');
const YAML = require('yamljs');
// -----------------------------

const app = express();
const PORT = process.env.PORT || 3000;

// --- 2. CARREGAR O ARQUIVO YAML ---
const swaggerDocument = YAML.load('./swagger.yaml');
// ----------------------------------
// --- Configuração do Banco de Dados ---
const pool = new Pool({
  user: process.env.DB_USER, // Seu usuário do banco
  host: process.env.DB_HOST, // Usando 127.0.0.1 que resolveu o erro 'InitPostgres'
  database: process.env.DB_DATABASE, // Seu nome do banco
  password: process.env.DB_PASSWORD, // Sua senha confirmada
  port: 5432,
});

// --- Middlewares Essenciais ---
app.use(cors()); // Permite que o Flutter acesse a API
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// --- 3. CONFIGURAR ROTA DO SWAGGER ---
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerDocument));
// --- Rotas da API ---


app.get('/', (req, res) => {
  res.send('API Sinaliza está online! Acesse /api-docs para documentação.');
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

// --- Rota de Dicionário ---
app.get('/dictionary', authMiddleware, async (req, res) => {
  try {
    const client = await pool.connect();
    try {
      const userId = req.user.id;
      const result = await client.query(`
        SELECT l.*, 
               CASE WHEN fs.sign_id IS NOT NULL THEN true ELSE false END as is_favorite 
        FROM lessons l 
        LEFT JOIN favorite_signs fs ON l.id = fs.sign_id AND fs.user_id = $1 
        ORDER BY l.title ASC
      `, [userId]);
      res.status(200).json(result.rows);
    } catch (dbError) {
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao buscar dicionário.' });
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

// --- Rota Toggle Favorite ---
app.post('/dictionary/favorite', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  const { sign_id } = req.body;

  if (!sign_id) return res.status(400).json({ message: 'sign_id é obrigatório.' });

  try {
    const client = await pool.connect();
    try {
      const check = await client.query('SELECT 1 FROM favorite_signs WHERE user_id = $1 AND sign_id = $2', [userId, sign_id]);
      if (check.rows.length > 0) {
        await client.query('DELETE FROM favorite_signs WHERE user_id = $1 AND sign_id = $2', [userId, sign_id]);
        res.status(200).json({ is_favorite: false });
      } else {
        await client.query('INSERT INTO favorite_signs (user_id, sign_id) VALUES ($1, $2)', [userId, sign_id]);
        res.status(201).json({ is_favorite: true });
      }
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro no favorite:', error);
    res.status(500).json({ message: 'Erro ao processar favorito.' });
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
          u.id, u.name, u.email, u.created_at, u.profile_picture, u.streak_count, u.last_practice_date,
          (COALESCE(SUM(p.score), 0) + COALESCE((SELECT SUM(score) FROM quiz_progress qp WHERE qp.user_id = u.id), 0)) as total_score
        FROM users u
        LEFT JOIN progress p ON u.id = p.user_id
        WHERE u.id = $1
        GROUP BY u.id, u.name, u.email, u.created_at, u.profile_picture, u.streak_count, u.last_practice_date
      `, [userId]);

      if (result.rows.length === 0) {
        return res.status(404).json({ message: 'Usuário não encontrado.' });
      }

      const user = result.rows[0];
      user.total_score = parseInt(user.total_score); // Garante número
      
      // Verifica se a ofensiva expirou
      let currentStreak = user.streak_count || 0;
      if (user.last_practice_date) {
        const now = new Date();
        const lastPractice = new Date(user.last_practice_date);
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const lastDay = new Date(lastPractice.getFullYear(), lastPractice.getMonth(), lastPractice.getDate());
        const diffDays = Math.round((today - lastDay) / (1000 * 60 * 60 * 24));
        
        if (diffDays > 1) {
          currentStreak = 0; // Se passou de ontem e não treinou, zera no visual
        }
      }
      user.streak_count = currentStreak;

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
    
    // Atualiza a ofensiva
    const userRes = await client.query('SELECT streak_count, last_practice_date FROM users WHERE id = $1', [userId]);
    let currentStreak = 0;
    if (userRes.rows.length > 0) {
      const user = userRes.rows[0];
      const now = new Date();
      const lastPractice = user.last_practice_date ? new Date(user.last_practice_date) : null;
      
      currentStreak = user.streak_count || 0;

      if (!lastPractice) {
        currentStreak = 1;
      } else {
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const lastDay = new Date(lastPractice.getFullYear(), lastPractice.getMonth(), lastPractice.getDate());
        const diffDays = Math.round((today - lastDay) / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
          currentStreak += 1;
        } else if (diffDays > 1) {
          currentStreak = 1;
        }
      }
      await client.query('UPDATE users SET streak_count = $1, last_practice_date = $2 WHERE id = $3', [currentStreak, now, userId]);
    }

    try {
      const result = await client.query(
        'INSERT INTO progress (user_id, lesson_id, score) VALUES ($1, $2, $3) RETURNING id',
        [userId, lesson_id, finalScore]
      );
      
      return res.status(201).json({ 
        message: `Progresso salvo! Você ganhou ${finalScore} pontos!`, 
        progressId: result.rows[0].id,
        streak_count: currentStreak
      });
    } catch (insertError) {
      if (insertError.code === '23505') {
        // Já completou, mas ofensiva foi salva!
        return res.status(200).json({ 
          message: 'Você já concluiu esta lição. Ofensiva atualizada!',
          streak_count: currentStreak 
        });
      }
      throw insertError;
    }

  } catch (error) {
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

// --- Rota de Quiz Status ---
app.get('/quiz/status', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  let client;
  try {
    client = await pool.connect();
    // Check if the user already played today
    const checkRes = await client.query(
      'SELECT id FROM quiz_progress WHERE user_id = $1 AND DATE(created_at) = CURRENT_DATE LIMIT 1',
      [userId]
    );
    const alreadyPlayed = checkRes.rows.length > 0;
    
    return res.status(200).json({ already_played: alreadyPlayed });
  } catch (error) {
    console.error('Erro na rota /quiz/status:', error);
    return res.status(500).json({ message: 'Erro ao verificar status do quiz.' });
  } finally {
    if (client) client.release();
  }
});

// --- Rota de Quiz Progress ---
app.post('/quiz/progress', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  const { score } = req.body;
  const finalScore = score || 5;
  let client;
  try {
    client = await pool.connect();
    
    // Check limit
    const checkRes = await client.query(
      'SELECT id FROM quiz_progress WHERE user_id = $1 AND DATE(created_at) = CURRENT_DATE LIMIT 1',
      [userId]
    );
    if (checkRes.rows.length > 0) {
      return res.status(400).json({ message: 'Você já completou o quiz de hoje!' });
    }

    // Atualiza ofensiva
    const userRes = await client.query('SELECT streak_count, last_practice_date FROM users WHERE id = $1', [userId]);
    let currentStreak = 0;
    if (userRes.rows.length > 0) {
      const user = userRes.rows[0];
      const now = new Date();
      const lastPractice = user.last_practice_date ? new Date(user.last_practice_date) : null;
      
      currentStreak = user.streak_count || 0;
      if (!lastPractice) {
        currentStreak = 1;
      } else {
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const lastDay = new Date(lastPractice.getFullYear(), lastPractice.getMonth(), lastPractice.getDate());
        const diffDays = Math.round((today - lastDay) / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
          currentStreak += 1;
        } else if (diffDays > 1) {
          currentStreak = 1;
        }
      }
      await client.query('UPDATE users SET streak_count = $1, last_practice_date = $2 WHERE id = $3', [currentStreak, now, userId]);
    }

    await client.query(
      'INSERT INTO quiz_progress (user_id, score) VALUES ($1, $2)',
      [userId, finalScore]
    );
    
    return res.status(201).json({ 
      message: `Progresso de quiz salvo! Você ganhou ${finalScore} pontos!`,
      streak_count: currentStreak
    });

  } catch (error) {
    console.error('Erro na rota /quiz/progress:', error);
    if (!res.headersSent) {
      return res.status(500).json({ message: 'Erro ao salvar quiz.' });
    }
  } finally {
    if (client) client.release();
  }
});

// --- Rota de Ranking ---
app.get('/ranking', authMiddleware, async (req, res) => {
  try {
    const client = await pool.connect();
    try {
      // Pega os top 50 usuários ordenados por XP (do maior para o menor)
      const result = await client.query(`
        SELECT 
          u.name, 
          u.profile_picture,
          (COALESCE(SUM(p.score), 0) + COALESCE((SELECT SUM(score) FROM quiz_progress qp WHERE qp.user_id = u.id), 0))::int as total_score
        FROM users u
        LEFT JOIN progress p ON u.id = p.user_id
        GROUP BY u.id, u.name, u.profile_picture
        ORDER BY total_score DESC
        LIMIT 50
      `);

      res.status(200).json(result.rows);

    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro no ranking:', error);
    res.status(500).json({ message: 'Erro ao buscar ranking.' });
  }
});

// --- Rota Admin: Listar Todos os Usuários ---
app.get('/admin/users', authMiddleware, async (req, res) => {
  try {
    const client = await pool.connect();
    try {
      const result = await client.query(`
        SELECT 
          id, 
          name, 
          email, 
          created_at, 
          profile_picture, 
          streak_count, 
          last_practice_date 
        FROM users 
        ORDER BY created_at DESC
      `);
      res.status(200).json(result.rows);
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro ao listar usuários:', error);
    res.status(500).json({ message: 'Erro ao listar usuários.' });
  }
});

// --- Rota Admin: Excluir Usuário (Banir) ---
app.delete('/admin/users/:id', authMiddleware, async (req, res) => {
  const userIdToDelete = req.params.id;
  try {
    const client = await pool.connect();
    try {
      // Deleta usuário (progresso é apagado por CASCADE no banco)
      const result = await client.query('DELETE FROM users WHERE id = $1 RETURNING id', [userIdToDelete]);
      if (result.rowCount === 0) {
        return res.status(404).json({ message: 'Usuário não encontrado.' });
      }
      res.status(200).json({ message: 'Usuário excluído com sucesso.' });
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro ao excluir usuário:', error);
    res.status(500).json({ message: 'Erro ao excluir usuário.' });
  }
});

// --- Rota Admin: Estatísticas Globais do Dashboard ---
app.get('/admin/stats', authMiddleware, async (req, res) => {
  try {
    const client = await pool.connect();
    try {
      const totalUsersRes = await client.query('SELECT COUNT(*) as count FROM users');
      const activeUsersRes = await client.query('SELECT COUNT(*) as count FROM users WHERE last_practice_date >= CURRENT_DATE - INTERVAL \'1 day\'');
      const streaksRes = await client.query('SELECT COUNT(*) as count FROM users WHERE streak_count > 0');
      
      const totalUsers = parseInt(totalUsersRes.rows[0].count);
      const accessesToday = parseInt(activeUsersRes.rows[0].count);
      const totalStreaks = parseInt(streaksRes.rows[0].count);
      
      res.status(200).json({
        total_users: totalUsers,
        accesses_today: accessesToday,
        total_streaks: totalStreaks
      });
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro no admin stats:', error);
    res.status(500).json({ message: 'Erro ao buscar estatísticas.' });
  }
});

// --- Rota de Cadastro ---
app.post('/users/register', async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ message: 'Nome, e-mail e senha são obrigatórios.' });
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({ message: 'Por favor, insira um e-mail válido (ex: nome@email.com).' });
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
          profile_picture: user.profile_picture,
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

app.put('/users/me', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  const { name, password, profile_picture } = req.body;

  try {
    const client = await pool.connect();
    try {
      // Monta a query dinamicamente (só atualiza o que foi enviado)
      let fields = [];
      let values = [];
      let paramCount = 1;

      if (name) {
        fields.push(`name = $${paramCount}`);
        values.push(name);
        paramCount++;
      }

      if (password) {
        // Se mandou senha, criptografa antes
        const salt = await bcrypt.genSalt(10);
        const passwordHash = await bcrypt.hash(password, salt);
        fields.push(`password_hash = $${paramCount}`);
        values.push(passwordHash);
        paramCount++;
      }

      if (profile_picture) {
        fields.push(`profile_picture = $${paramCount}`);
        values.push(profile_picture);
        paramCount++;
      }

      if (fields.length === 0) {
        return res.status(400).json({ message: 'Nenhum dado para atualizar.' });
      }

      // Adiciona o ID no final dos valores
      values.push(userId);
      
      const query = `UPDATE users SET ${fields.join(', ')} WHERE id = $${paramCount}`;
      
      await client.query(query, values);
      
      res.status(200).json({ message: 'Dados atualizados com sucesso!' });

    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro ao atualizar:', error);
    if (error.code === '23505') {
        return res.status(409).json({ message: 'Este nome já está em uso.' });
    }
    res.status(500).json({ message: 'Erro no servidor.' });
  }
});

app.delete('/users/me', authMiddleware, async (req, res) => {
  const userId = req.user.id;

  try {
    const client = await pool.connect();
    try {
      // Como configuramos o banco com CASCADE, apagar o user apaga o progresso junto
      await client.query('DELETE FROM users WHERE id = $1', [userId]);
      
      res.status(200).json({ message: 'Conta excluída com sucesso. Adeus!' });

    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro ao excluir:', error);
    res.status(500).json({ message: 'Erro no servidor.' });
  }
});
// --- DEBUG: TESTE DE CONEXÃO AO INICIAR ---
(async () => {
  try {
    const client = await pool.connect();
    console.log("---------------------------------------------------------");
    
    // 1. Qual banco estou usando?
    const dbRes = await client.query('SELECT current_database()');
    console.log(`🔌 Conectado no banco: [ ${dbRes.rows[0].current_database} ]`);

    // 2. Quais tabelas existem aqui?
    const tablesRes = await client.query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public'
    `);
    
    const tables = tablesRes.rows.map(row => row.table_name);
    console.log(`📋 Tabelas encontradas: ${tables.length > 0 ? tables.join(', ') : 'NENHUMA (Banco Vazio!)'}`);
    console.log("---------------------------------------------------------");
    
    client.release();
  } catch (err) {
    console.error('❌ Erro fatal ao conectar no banco:', err.message);
  }
})();
// ------------------------------------------

// app.listen ...
// --- Iniciar o Servidor ---
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Servidor Node.js rodando na porta http://localhost:${PORT}`);
});