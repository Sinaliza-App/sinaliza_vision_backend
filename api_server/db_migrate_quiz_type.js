const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function migrate() {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    console.log('1. Adicionando colunas type e module_id em quiz_progress se não existirem...');
    await client.query(`
      ALTER TABLE quiz_progress ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT 'quiz';
      ALTER TABLE quiz_progress ADD COLUMN IF NOT EXISTS module_id INTEGER;
    `);

    console.log('2. Atualizando registros existentes para type = quiz...');
    await client.query(`
      UPDATE quiz_progress SET type = 'quiz' WHERE type IS NULL;
    `);

    console.log('3. Atualizando desafio realizado hoje (ID 19) para type = challenge...');
    await client.query(`
      UPDATE quiz_progress SET type = 'challenge' WHERE id = 19;
    `);

    await client.query('COMMIT');
    console.log('✅ Migração de quiz_progress concluída com sucesso!');

    const res = await client.query('SELECT * FROM quiz_progress ORDER BY id DESC LIMIT 5');
    console.log('Últimos registros de quiz_progress:', res.rows);
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('❌ Erro na migração:', err);
  } finally {
    client.release();
    await pool.end();
  }
}

migrate();
