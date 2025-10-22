const express = require('express');
const cors = require('cors');
const bcrypt = require('bcryptjs');
const { Pool } = require('pg'); // 1. Importe o 'Pool' do 'pg'
require('dotenv').config(); // 2. Importe e configure o 'dotenv' NO TOPO

const app = express();
const port = 3000;

// --- Configuração do Banco de Dados ---
// 3. Crie o "Pool" de conexões usando as variáveis do .env
const pool = new Pool({
  user: 'postgres',
  host: 'localhost',
  database: 'sinaliza_db',
  password: 'Sinaliza282006#',
  port: 5432,
});
// Middlewares
app.use(cors());
app.use(express.json());

// --- Rotas da API ---

app.get('/', (req, res) => {
  res.send('A API de Usuários (Node.js) do Sinaliza está funcionando!');
});

// Rota para cadastrar um novo usuário (MODIFICADA)
app.post('/users/register', async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ message: 'Nome, e-mail e senha são obrigatórios.' });
    }

    const salt = await bcrypt.genSalt(10);
    const passwordHash = await bcrypt.hash(password, salt);

    console.log('Recebido novo cadastro:');
    console.log({ name, email, passwordHash });

    // 4. Salve no Banco de Dados
    const client = await pool.connect(); // Pega uma conexão do pool
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
      // Erro específico do banco (ex: violação de constraint)
      console.error('Erro no banco de dados:', dbError);
      res.status(500).json({ message: 'Erro ao salvar usuário no banco.' });
    } finally {
      client.release(); // 5. Libera a conexão de volta para o pool
    }

  } catch (error) {
    console.error('Erro geral no servidor:', error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

// Iniciar o Servidor
app.listen(port, () => {
  console.log(`Servidor Node.js rodando na porta http://localhost:${port}`);
});