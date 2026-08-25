const jwt = require('jsonwebtoken');
const pool = require('./db');

const authMiddleware = async (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (token == null) {
    return res.status(401).json({ message: 'Acesso negado. Nenhum token fornecido.' });
  }

  try {
    // IMPORTANTE: Agora usamos a chave secreta JWT do Supabase, não a nossa antiga!
    if (!process.env.SUPABASE_JWT_SECRET) {
      console.error("FATAL: SUPABASE_JWT_SECRET não está definida no .env");
      return res.status(500).json({ message: 'Erro de configuração do servidor.' });
    }

    const payload = jwt.verify(token, process.env.SUPABASE_JWT_SECRET);
    
    // O payload.sub do Supabase contém o UUID do usuário em auth.users
    const authId = payload.sub;

    // Precisamos achar qual é o ID numérico deste usuário na NOSSA tabela public.users
    const client = await pool.connect();
    try {
      const result = await client.query('SELECT id, is_admin FROM users WHERE auth_id = $1', [authId]);
      
      if (result.rows.length === 0) {
        return res.status(401).json({ message: 'Usuário não encontrado na base de dados (Sincronização pendente).' });
      }

      // Anexa os dados completos para a próxima rota
      req.user = {
        id: result.rows[0].id, // O ID numérico antigo (para não quebrar progressos/quizzes)
        auth_id: authId,
        is_admin: result.rows[0].is_admin
      };

      next();
    } finally {
      client.release();
    }

  } catch (ex) {
    console.error('Erro no AuthMiddleware:', ex.message);
    res.status(401).json({ message: 'Token inválido ou expirado.' });
  }
};

module.exports = authMiddleware;