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
    
    // Create favorite_signs table
    await client.query(`
      CREATE TABLE IF NOT EXISTS favorite_signs (
        user_id integer NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
        sign_id integer NOT NULL,
        created_at timestamp without time zone DEFAULT now(),
        UNIQUE(user_id, sign_id)
      );
    `);
    console.log('Tabela favorite_signs verificada/criada com sucesso.');

    // Create quiz_progress table
    await client.query(`
      CREATE TABLE IF NOT EXISTS quiz_progress (
        id SERIAL PRIMARY KEY,
        user_id integer NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
        score integer NOT NULL,
        created_at timestamp without time zone DEFAULT now()
      );
    `);
    console.log('Tabela quiz_progress verificada/criada com sucesso.');

    await client.query('COMMIT');
    console.log('Migração finalizada com sucesso!');
  } catch (e) {
    await client.query('ROLLBACK');
    console.error('Erro na migração:', e);
  } finally {
    client.release();
    pool.end();
  }
}

migrate();
