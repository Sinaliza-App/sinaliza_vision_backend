require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_DATABASE,
  password: process.env.DB_PASSWORD,
  port: process.env.DB_PORT || 5432,
});

(async () => {
  try {
    const client = await pool.connect();
    try {
      await client.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture TEXT;');
      console.log('Coluna profile_picture garantida com sucesso.');

      await client.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_count INT DEFAULT 0;');
      console.log('Coluna streak_count garantida com sucesso.');

      await client.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS last_practice_date TIMESTAMP;');
      console.log('Coluna last_practice_date garantida com sucesso.');

      await client.query('ALTER TABLE lessons ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;');
      console.log('Coluna thumbnail_url garantida na tabela lessons com sucesso.');

      await client.query('ALTER TABLE lessons ADD COLUMN IF NOT EXISTS gif_url TEXT;');
      console.log('Coluna gif_url garantida na tabela lessons com sucesso.');

      await client.query("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT 'estatico';");
      console.log('Coluna type garantida na tabela lessons com sucesso.');
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
