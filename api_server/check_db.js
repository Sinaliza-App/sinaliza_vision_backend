require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_DATABASE,
  password: process.env.DB_PASSWORD,
  port: 5432,
});

(async () => {
  try {
    const client = await pool.connect();
    try {
      await client.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture TEXT;');
      console.log('Coluna profile_picture garantida com sucesso.');
    } catch(e) {
      console.log('Erro ao adicionar coluna:', e);
    } finally {
      client.release();
    }
  } catch (err) {
    console.error('Erro de conexão:', err);
  } finally {
    pool.end();
  }
})();
