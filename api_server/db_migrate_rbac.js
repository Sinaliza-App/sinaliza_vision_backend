require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function migrateRBAC() {
  const client = await pool.connect();
  try {
    console.log('Iniciando migração de RBAC (Row Level Security para Admins)...');

    // 1. Tabela Lessons
    console.log('1. Atualizando RLS na tabela lessons para restringir escrita a Admins...');
    await client.query(`
      ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
      
      -- Todos podem ler
      DROP POLICY IF EXISTS "Usuários autenticados podem ver lições" ON lessons;
      CREATE POLICY "Usuários autenticados podem ver lições" 
      ON lessons FOR SELECT 
      TO authenticated
      USING (true);

      -- Somente admins podem modificar lições
      DROP POLICY IF EXISTS "Somente admins podem modificar lições" ON lessons;
      CREATE POLICY "Somente admins podem modificar lições" 
      ON lessons FOR ALL 
      TO authenticated
      USING (
        (SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true
      )
      WITH CHECK (
        (SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true
      );
    `);

    // 2. Tabela Modules
    console.log('2. Atualizando RLS na tabela modules para restringir escrita a Admins...');
    await client.query(`
      ALTER TABLE modules ENABLE ROW LEVEL SECURITY;

      -- Todos podem ler
      DROP POLICY IF EXISTS "Usuários autenticados podem ver módulos" ON modules;
      CREATE POLICY "Usuários autenticados podem ver módulos" 
      ON modules FOR SELECT 
      TO authenticated
      USING (true);

      DROP POLICY IF EXISTS "Somente admins podem modificar modulos" ON modules;
      CREATE POLICY "Somente admins podem modificar modulos" 
      ON modules FOR ALL 
      TO authenticated
      USING (
        (SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true
      )
      WITH CHECK (
        (SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true
      );
    `);

    console.log('✅ Migração de RBAC concluída com sucesso!');
  } catch (err) {
    console.error('❌ Erro na migração de RBAC:', err);
  } finally {
    client.release();
    pool.end();
  }
}

migrateRBAC();
