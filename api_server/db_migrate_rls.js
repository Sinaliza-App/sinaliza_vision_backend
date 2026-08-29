require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function migrateRLS() {
  const client = await pool.connect();
  try {
    console.log('Iniciando migração de RLS (Row Level Security)...');

    // 1. users
    console.log('1. Configurando RLS na tabela users...');
    await client.query(`
      ALTER TABLE users ENABLE ROW LEVEL SECURITY;
      
      -- Policy para leitura (SELECT)
      DROP POLICY IF EXISTS "Usuários podem ver seu próprio perfil" ON users;
      CREATE POLICY "Usuários podem ver seu próprio perfil" 
      ON users FOR SELECT 
      TO authenticated
      USING (auth_id = auth.uid());

      -- Policy para atualização (UPDATE)
      DROP POLICY IF EXISTS "Usuários podem atualizar seu próprio perfil" ON users;
      CREATE POLICY "Usuários podem atualizar seu próprio perfil" 
      ON users FOR UPDATE 
      TO authenticated
      USING (auth_id = auth.uid());
    `);

    // 2. modules e lessons
    console.log('2. Configurando RLS na tabela modules e lessons...');
    await client.query(`
      ALTER TABLE modules ENABLE ROW LEVEL SECURITY;
      ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;

      -- Todos os usuários logados podem ler os módulos
      DROP POLICY IF EXISTS "Usuários autenticados podem ver módulos" ON modules;
      CREATE POLICY "Usuários autenticados podem ver módulos" 
      ON modules FOR SELECT 
      TO authenticated
      USING (true);

      -- Todos os usuários logados podem ler as lições
      DROP POLICY IF EXISTS "Usuários autenticados podem ver lições" ON lessons;
      CREATE POLICY "Usuários autenticados podem ver lições" 
      ON lessons FOR SELECT 
      TO authenticated
      USING (true);
    `);

    // 3. progress
    console.log('3. Configurando RLS na tabela progress...');
    await client.query(`
      ALTER TABLE progress ENABLE ROW LEVEL SECURITY;

      DROP POLICY IF EXISTS "Usuários podem gerenciar seu próprio progresso" ON progress;
      CREATE POLICY "Usuários podem gerenciar seu próprio progresso" 
      ON progress FOR ALL 
      TO authenticated
      USING (
        user_id = (SELECT id FROM public.users WHERE auth_id = auth.uid())
      );
    `);

    // 4. quiz_progress
    console.log('4. Configurando RLS na tabela quiz_progress...');
    await client.query(`
      ALTER TABLE quiz_progress ENABLE ROW LEVEL SECURITY;

      DROP POLICY IF EXISTS "Usuários podem gerenciar seu próprio progresso de quiz" ON quiz_progress;
      CREATE POLICY "Usuários podem gerenciar seu próprio progresso de quiz" 
      ON quiz_progress FOR ALL 
      TO authenticated
      USING (
        user_id = (SELECT id FROM public.users WHERE auth_id = auth.uid())
      );
    `);

    // 5. favorite_signs
    console.log('5. Configurando RLS na tabela favorite_signs...');
    await client.query(`
      ALTER TABLE favorite_signs ENABLE ROW LEVEL SECURITY;

      DROP POLICY IF EXISTS "Usuários podem gerenciar seus favoritos" ON favorite_signs;
      CREATE POLICY "Usuários podem gerenciar seus favoritos" 
      ON favorite_signs FOR ALL 
      TO authenticated
      USING (
        user_id = (SELECT id FROM public.users WHERE auth_id = auth.uid())
      );
    `);

    console.log('✅ Migração de RLS concluída com sucesso!');
  } catch (err) {
    console.error('❌ Erro na migração de RLS:', err);
  } finally {
    client.release();
    pool.end();
  }
}

migrateRLS();
