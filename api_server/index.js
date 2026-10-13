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
const pool = require('./db');

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
          m.is_draft,
          COUNT(l.id)::int as total_lessons,
          COUNT(p.id)::int as completed_lessons
        FROM modules m
        LEFT JOIN lessons l ON m.id = l.module_id AND l.is_draft = false
        LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = $1
        WHERE m.is_draft = false OR (SELECT is_admin FROM users WHERE id = $1) = true
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
      let query = 'SELECT * FROM lessons WHERE (is_draft = false OR (SELECT is_admin FROM users WHERE id = $1) = true)';
      let params = [req.user.id];

      if (module_id) {
        query += ' AND module_id = $2';
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
          u.id, u.name, u.email, u.created_at, u.profile_picture, u.streak_count, u.last_practice_date, u.is_admin,
          COALESCE(u.role, CASE WHEN u.is_admin = true THEN 'admin' ELSE 'student' END) as role,
          (COALESCE(SUM(p.score), 0) + COALESCE((SELECT SUM(score) FROM quiz_progress qp WHERE qp.user_id = u.id), 0)) as total_score
        FROM users u
        LEFT JOIN progress p ON u.id = p.user_id
        WHERE u.id = $1
        GROUP BY u.id, u.name, u.email, u.created_at, u.profile_picture, u.streak_count, u.last_practice_date, u.is_admin, u.role
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
    // Check if the user already played today (filtra apenas quiz, ignorando desafios práticos)
    const checkRes = await client.query(
      "SELECT id FROM quiz_progress WHERE user_id = $1 AND (type = 'quiz' OR type IS NULL) AND DATE(created_at) = CURRENT_DATE LIMIT 1",
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
    
    // Check limit (apenas quiz)
    const checkRes = await client.query(
      "SELECT id FROM quiz_progress WHERE user_id = $1 AND (type = 'quiz' OR type IS NULL) AND DATE(created_at) = CURRENT_DATE LIMIT 1",
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
      "INSERT INTO quiz_progress (user_id, score, type) VALUES ($1, $2, 'quiz')",
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

// --- Rota de Desafio Final Progress (Boss) ---
app.post('/challenge/progress', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  const { score, module_id } = req.body;
  const finalScore = score || 50;
  let client;
  try {
    client = await pool.connect();

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

    // Salva pontuação para contar no ranking e perfil com type = 'challenge'
    await client.query(
      "INSERT INTO quiz_progress (user_id, score, type, module_id) VALUES ($1, $2, 'challenge', $3)",
      [userId, finalScore, module_id || null]
    );

    return res.status(201).json({
      message: `Desafio final concluído! +${finalScore} XP!`,
      streak_count: currentStreak
    });
  } catch (error) {
    console.error('Erro na rota /challenge/progress:', error);
    if (!res.headersSent) {
      return res.status(500).json({ message: 'Erro ao salvar progresso do desafio.' });
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

// --- Rota Admin/Teacher: Listar Todos os Usuários ---
app.get('/admin/users', authMiddleware, async (req, res) => {
  const isAuthorized = req.user.role === 'teacher' || req.user.role === 'admin' || req.user.is_admin;
  if (!isAuthorized) {
    return res.status(403).json({ message: 'Acesso negado: Apenas professores e administradores podem listar usuários.' });
  }

  try {
    const client = await pool.connect();
    try {
      const result = await client.query(`
        SELECT 
          id, 
          auth_id,
          name, 
          email, 
          created_at, 
          profile_picture, 
          streak_count, 
          last_practice_date,
          is_admin,
          COALESCE(role, CASE WHEN is_admin = true THEN 'admin' ELSE 'student' END) AS role
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

// --- Rota Admin: Alterar Papel do Usuário (EXCLUSIVO ADMIN) ---
app.put('/admin/users/:id/role', authMiddleware, async (req, res) => {
  if (req.user.role !== 'admin' && !req.user.is_admin) {
    return res.status(403).json({ message: 'Acesso negado: Apenas administradores gerais podem alterar privilégios.' });
  }

  const userIdToUpdate = req.params.id;
  const { role } = req.body;

  if (!['student', 'teacher', 'admin'].includes(role)) {
    return res.status(400).json({ message: "Papel inválido. Opções válidas: 'student', 'teacher', 'admin'." });
  }

  const isAdmin = (role === 'admin');

  try {
    const client = await pool.connect();
    try {
      const result = await client.query(
        'UPDATE users SET role = $1, is_admin = $2 WHERE id = $3 RETURNING id, name, role, is_admin',
        [role, isAdmin, userIdToUpdate]
      );

      if (result.rowCount === 0) {
        return res.status(404).json({ message: 'Usuário não encontrado.' });
      }

      res.status(200).json({
        message: `Papel do usuário atualizado para ${role.toUpperCase()} com sucesso.`,
        user: result.rows[0]
      });
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Erro ao atualizar papel do usuário:', error);
    res.status(500).json({ message: 'Erro ao atualizar privilégios do usuário.' });
  }
});

// --- Rota Admin: Excluir Usuário (Banir) (EXCLUSIVO ADMIN) ---
app.delete('/admin/users/:id', authMiddleware, async (req, res) => {
  // SEGURANÇA: Professores NÃO podem banir contas! Apenas administradores do sistema.
  if (req.user.role !== 'admin' && !req.user.is_admin) {
    return res.status(403).json({ 
      message: 'Acesso negado: Professores não têm permissão para excluir contas de alunos. Apenas Administradores do Sistema podem banir contas.' 
    });
  }

  const userIdToDelete = req.params.id;
  try {
    const client = await pool.connect();
    try {
      // Deleta usuário (progresso é apagado por CASCADE no banco)
      const result = await client.query('DELETE FROM users WHERE id = $1 RETURNING id', [userIdToDelete]);
      if (result.rowCount === 0) {
        return res.status(404).json({ message: 'Usuário não encontrado.' });
      }
      res.status(200).json({ message: 'Usuário excluído com sucesso pelo administrador.' });
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

// ROTAS DE LOGIN E REGISTER FORAM REMOVIDAS (Agora gerenciadas pelo Supabase Auth)

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

// ==============================================================================
// --- ROTAS DO PIPELINE DE COLETA & FEEDBACK DE DADOS PARA TREINAMENTO DE IA ---
// ==============================================================================

// 1. Enviar nova amostra gravada (Mobile App ou Web Data Studio)
app.post('/coleta/amostra', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  const authId = req.user.auth_id;
  const { sign_name, mode, raw_landmarks, source, reporter_role } = req.body;

  if (!sign_name || typeof sign_name !== 'string') {
    return res.status(400).json({ message: 'O nome do sinal (sign_name) é obrigatório.' });
  }

  if (!raw_landmarks || !Array.isArray(raw_landmarks) || raw_landmarks.length === 0) {
    return res.status(400).json({ message: 'Sequência de keypoints (raw_landmarks) vazia ou inválida.' });
  }

  const role = reporter_role || req.user.role || 'aluno';
  const isTeacher = role === 'professor' || req.user.role === 'teacher' || req.user.role === 'admin' || req.user.is_admin;
  const targetStatus = isTeacher ? 'validado' : 'pendente';
  const targetMode = mode || (raw_landmarks.length === 20 ? 'alfabeto' : 'dinamico');

  let client;
  try {
    client = await pool.connect();
    
    // Grava no banco de feedback/coleta
    const insertRes = await client.query(`
      INSERT INTO feedback_samples (
        user_id, auth_id, sign_name, mode, raw_landmarks, status, 
        reporter_role, device_info, created_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
      RETURNING id, status
    `, [
      userId, 
      authId, 
      sign_name.trim().toLowerCase(), 
      targetMode, 
      JSON.stringify(raw_landmarks), 
      targetStatus, 
      isTeacher ? 'professor' : 'aluno', 
      source || 'mobile'
    ]);

    const sampleId = insertRes.rows[0].id;
    let earnedXp = 0;

    // Se enviado por um estudante, recompensa com +10 XP no progresso geral
    if (!isTeacher) {
      earnedXp = 10;
      try {
        await client.query(`
          INSERT INTO quiz_progress (user_id, score, type) 
          VALUES ($1, $2, 'dataset_contribution')
        `, [userId, earnedXp]);
      } catch (scoreErr) {
        console.warn('Aviso: Não foi possível computar XP na tabela quiz_progress:', scoreErr.message);
      }
    }

    return res.status(201).json({
      success: true,
      message: isTeacher 
        ? 'Amostra docente registrada com selo de validada!' 
        : `Amostra enviada para revisão do professor! +${earnedXp} XP`,
      sample_id: sampleId,
      status: targetStatus,
      xp_awarded: earnedXp
    });

  } catch (error) {
    console.error('Erro na rota /coleta/amostra:', error);
    return res.status(500).json({ message: 'Erro ao registrar amostra no banco de dados: ' + error.message });
  } finally {
    if (client) client.release();
  }
});

// 2. Listar amostras para curadoria (Exclusivo Professores e Admins)
app.get('/coleta/amostras', authMiddleware, async (req, res) => {
  const isAuthorized = req.user.role === 'teacher' || req.user.role === 'admin' || req.user.is_admin;
  if (!isAuthorized) {
    return res.status(403).json({ message: 'Acesso negado: Recurso exclusivo para educadores e administradores.' });
  }

  const { status, sign_name, limit = 50, offset = 0 } = req.query;
  let client;
  try {
    client = await pool.connect();
    let query = `
      SELECT 
        fs.id,
        fs.user_id,
        fs.sign_name,
        fs.mode,
        fs.status,
        fs.reporter_role,
        fs.corrected_sign,
        fs.device_info,
        fs.created_at,
        fs.evaluated_at,
        u.name as student_name,
        u.email as student_email,
        jsonb_array_length(fs.raw_landmarks) as frame_count
      FROM feedback_samples fs
      LEFT JOIN users u ON fs.user_id = u.id
      WHERE 1=1
    `;
    const params = [];

    if (status && status !== 'all') {
      params.push(status);
      query += ` AND fs.status = $${params.length}`;
    }

    if (sign_name) {
      params.push(sign_name.trim().toLowerCase());
      query += ` AND fs.sign_name = $${params.length}`;
    }

    query += ` ORDER BY fs.created_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    params.push(parseInt(limit), parseInt(offset));

    const result = await client.query(query, params);
    return res.status(200).json(result.rows);

  } catch (error) {
    console.error('Erro ao listar amostras:', error);
    return res.status(500).json({ message: 'Erro ao listar amostras para curadoria: ' + error.message });
  } finally {
    if (client) client.release();
  }
});

// 3. Avaliar amostra: Aprovar, Corrigir ou Rejeitar (Exclusivo Professores e Admins)
app.patch('/coleta/amostras/:id/avaliar', authMiddleware, async (req, res) => {
  const isAuthorized = req.user.role === 'teacher' || req.user.role === 'admin' || req.user.is_admin;
  if (!isAuthorized) {
    return res.status(403).json({ message: 'Acesso negado: Recurso exclusivo para educadores e administradores.' });
  }

  const sampleId = req.params.id;
  const { status, corrected_sign, evaluator_notes } = req.body;

  if (!['validado', 'rejeitado', 'pendente'].includes(status)) {
    return res.status(400).json({ message: "Status inválido. Escolha 'validado', 'rejeitado' ou 'pendente'." });
  }

  let client;
  try {
    client = await pool.connect();
    const updateRes = await client.query(`
      UPDATE feedback_samples 
      SET 
        status = $1,
        corrected_sign = COALESCE($2, corrected_sign),
        evaluator_id = $3,
        evaluator_notes = $4,
        evaluated_at = NOW()
      WHERE id = $5
      RETURNING id, status, corrected_sign
    `, [status, corrected_sign || null, req.user.id, evaluator_notes || null, sampleId]);

    if (updateRes.rowCount === 0) {
      return res.status(404).json({ message: 'Amostra não encontrada.' });
    }

    return res.status(200).json({
      message: `Amostra #${sampleId} marcada como ${status.toUpperCase()}!`,
      sample: updateRes.rows[0]
    });

  } catch (error) {
    console.error('Erro ao avaliar amostra:', error);
    return res.status(500).json({ message: 'Erro ao registrar avaliação da amostra.' });
  } finally {
    if (client) client.release();
  }
});

// 4. Estatísticas de Coleta e Metas por Classe
app.get('/coleta/stats', authMiddleware, async (req, res) => {
  const isAuthorized = req.user.role === 'teacher' || req.user.role === 'admin' || req.user.is_admin;
  if (!isAuthorized) {
    return res.status(403).json({ message: 'Acesso negado.' });
  }

  let client;
  try {
    client = await pool.connect();
    
    // Totalizadores gerais
    const totalsRes = await client.query(`
      SELECT 
        COUNT(*)::int as total_samples,
        COUNT(CASE WHEN status = 'pendente' THEN 1 END)::int as pending_count,
        COUNT(CASE WHEN status = 'validado' THEN 1 END)::int as validated_count,
        COUNT(CASE WHEN status = 'rejeitado' THEN 1 END)::int as rejected_count
      FROM feedback_samples
    `);

    // Contagem por sinal validado
    const perSignRes = await client.query(`
      SELECT 
        COALESCE(corrected_sign, sign_name) as sign_name,
        mode,
        COUNT(*)::int as total_collected,
        COUNT(CASE WHEN status = 'validado' THEN 1 END)::int as validated_samples,
        COUNT(CASE WHEN status = 'pendente' THEN 1 END)::int as pending_samples
      FROM feedback_samples
      GROUP BY COALESCE(corrected_sign, sign_name), mode
      ORDER BY validated_samples DESC, total_collected DESC
    `);

    return res.status(200).json({
      overview: totalsRes.rows[0] || { total_samples: 0, pending_count: 0, validated_count: 0, rejected_count: 0 },
      per_sign: perSignRes.rows || []
    });

  } catch (error) {
    console.error('Erro ao buscar estatísticas de coleta:', error);
    return res.status(500).json({ message: 'Erro ao carregar métricas do dataset: ' + error.message });
  } finally {
    if (client) client.release();
  }
});

// 5. Exportar Manifesto do Dataset para Retreinamento Local (Python)
app.get('/coleta/exportar-manifesto', authMiddleware, async (req, res) => {
  const isAuthorized = req.user.role === 'teacher' || req.user.role === 'admin' || req.user.is_admin;
  if (!isAuthorized) {
    return res.status(403).json({ message: 'Acesso negado.' });
  }

  let client;
  try {
    client = await pool.connect();
    const result = await client.query(`
      SELECT 
        id,
        COALESCE(corrected_sign, sign_name) as sign_name,
        mode,
        raw_landmarks,
        created_at
      FROM feedback_samples
      WHERE status = 'validado'
      ORDER BY id ASC
    `);

    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', 'attachment; filename="sinaliza_validated_dataset.json"');
    return res.status(200).json({
      exported_at: new Date().toISOString(),
      total_validated: result.rows.length,
      samples: result.rows
    });

  } catch (error) {
    console.error('Erro ao exportar manifesto:', error);
    return res.status(500).json({ message: 'Erro ao gerar exportação do dataset.' });
  } finally {
    if (client) client.release();
  }
});

// 6. Verificar Código Institucional de Professor
app.post('/auth/verify-teacher-code', async (req, res) => {
  const { code } = req.body;
  if (!code) {
    return res.status(400).json({ valid: false, message: 'Código não informado.' });
  }
  const defaultCode = process.env.TEACHER_ACCESS_CODE || 'PROF-SINALIZA-2026';
  const isValid = code.trim().toUpperCase() === defaultCode.toUpperCase();
  return res.status(200).json({ valid: isValid });
});

// 7. Reivindicar papel de Professor com Código Institucional
app.post('/auth/claim-teacher', authMiddleware, async (req, res) => {
  const { code } = req.body;
  const defaultCode = process.env.TEACHER_ACCESS_CODE || 'PROF-SINALIZA-2026';

  if (!code || code.trim().toUpperCase() !== defaultCode.toUpperCase()) {
    return res.status(400).json({ message: 'Código de autorização docente inválido.' });
  }

  let client;
  try {
    client = await pool.connect();
    await client.query("UPDATE users SET role = 'teacher' WHERE id = $1", [req.user.id]);
    return res.status(200).json({ message: 'Permissão docente concedida com sucesso!' });
  } catch (err) {
    console.error('Erro ao atualizar papel:', err);
    return res.status(500).json({ message: 'Erro ao processar solicitação.' });
  } finally {
    if (client) client.release();
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