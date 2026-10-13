const { createClient } = require('@supabase/supabase-js');
const pool = require('./db');

const supabase = createClient(
  process.env.VITE_SUPABASE_URL,
  process.env.VITE_SUPABASE_ANON_KEY
);

const authMiddleware = async (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (token == null) {
    return res.status(401).json({ message: 'Acesso negado. Nenhum token fornecido.' });
  }

  try {
    const { data: { user }, error } = await supabase.auth.getUser(token);
    
    if (error || !user) {
      console.error("Supabase Auth Error:", error?.message);
      return res.status(401).json({ message: 'Token inválido ou expirado.' });
    }
    
    // O payload do Supabase contém o UUID do usuário em auth.users
    const authId = user.id;

    // Precisamos achar qual é o ID numérico deste usuário na NOSSA tabela public.users
    const client = await pool.connect();
    try {
      const result = await client.query(`
        SELECT id, is_admin, 
               COALESCE(role, CASE WHEN is_admin = true THEN 'admin' ELSE 'student' END) AS role 
        FROM users 
        WHERE auth_id = $1
      `, [authId]);
      
      if (result.rows.length === 0) {
        return res.status(401).json({ message: 'Usuário não encontrado na base de dados (Sincronização pendente).' });
      }

      const userRow = result.rows[0];
      const userRole = userRow.role || (userRow.is_admin ? 'admin' : 'student');

      // Anexa os dados completos para a próxima rota
      req.user = {
        id: userRow.id,
        auth_id: authId,
        is_admin: userRow.is_admin === true || userRole === 'admin',
        role: userRole
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