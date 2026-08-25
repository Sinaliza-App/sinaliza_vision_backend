const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_DATABASE,
  password: process.env.DB_PASSWORD,
  port: 5432
});

async function migrate() {
  const client = await pool.connect();
  try {
    console.log('Iniciando migração do banco...');

    // 1. Limpar banco (usuários e progresso em cascata)
    console.log('1. Apagando todos os usuários atuais...');
    await client.query('TRUNCATE TABLE users CASCADE');

    // 2. Modificar tabela users
    console.log('2. Atualizando estrutura da tabela users...');
    // Remover password_hash
    await client.query('ALTER TABLE users DROP COLUMN IF EXISTS password_hash');
    // Adicionar colunas novas
    await client.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_id UUID UNIQUE');
    await client.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE');

    // 3. Criar função de Trigger para sincronizar auth.users -> public.users
    console.log('3. Criando trigger function de sincronização do Supabase Auth...');
    await client.query(`
      CREATE OR REPLACE FUNCTION public.handle_new_user()
      RETURNS trigger AS $$
      BEGIN
        INSERT INTO public.users (auth_id, name, email, is_admin)
        VALUES (
          new.id, 
          COALESCE(new.raw_user_meta_data->>'name', 'Aluno'), 
          new.email,
          FALSE
        );
        RETURN new;
      END;
      $$ LANGUAGE plpgsql SECURITY DEFINER;
    `);

    // 4. Criar o Trigger (Se não existir)
    console.log('4. Criando trigger no auth.users...');
    await client.query(`
      DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
      CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
    `);

    console.log('✅ Migração do banco concluída com sucesso!');
  } catch (err) {
    console.error('❌ Erro durante a migração:', err);
  } finally {
    client.release();
    await pool.end();
  }
}

migrate();
