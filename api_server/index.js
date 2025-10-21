const express = require('express');
const cors = require('cors');
const bcrypt = require('bcryptjs');
const app = express();
const port = 3000; // Ou use process.env.PORT

// --- Middlewares Essenciais ---
app.use(cors()); // Habilita o CORS
app.use(express.json()); // Habilita o Express para ler JSON

// --- Rotas da API ---

// Rota de teste
app.get('/', (req, res) => {
  res.send('A API de Usuários (Node.js) do Sinaliza está funcionando!');
});

// Rota para cadastrar um novo usuário
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

    // TODO: Inserir o usuário no seu banco de dados (PostgreSQL, MySQL, etc.)
    // Ex: const result = await pool.query(...)

    res.status(201).json({ 
      message: 'Usuário cadastrado com sucesso!', 
      // userId: result.rows[0].id 
    });

  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Erro no servidor' });
  }
});

// --- Iniciar o Servidor ---
app.listen(port, () => {
  console.log(`Servidor Node.js rodando na porta http://localhost:${port}`);
});