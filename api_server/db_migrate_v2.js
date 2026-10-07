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
    console.log('Iniciando migração V2 (Drafts, Reports, Notificações)...');

    // 1. Drafts
    console.log('1. Adicionando is_draft...');
    await client.query('ALTER TABLE public.lessons ADD COLUMN IF NOT EXISTS is_draft BOOLEAN DEFAULT false;');
    await client.query('ALTER TABLE public.modules ADD COLUMN IF NOT EXISTS is_draft BOOLEAN DEFAULT false;');

    // 2. Tabela de Denúncias/Reports
    console.log('2. Criando tabela reports...');
    await client.query(`
      CREATE TABLE IF NOT EXISTS public.reports (
          id SERIAL PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
          target_type TEXT NOT NULL CHECK (target_type IN ('lesson', 'sign', 'quiz')),
          target_id INTEGER NOT NULL,
          description TEXT NOT NULL,
          status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'resolved')),
          created_at TIMESTAMP DEFAULT now()
      );
    `);

    // 3. Tabela de Notificações
    console.log('3. Criando tabela notifications...');
    await client.query(`
      CREATE TABLE IF NOT EXISTS public.notifications (
          id SERIAL PRIMARY KEY,
          title TEXT NOT NULL,
          message TEXT NOT NULL,
          created_by UUID REFERENCES auth.users(id),
          created_at TIMESTAMP DEFAULT now()
      );
    `);

    // 4. Configurar RLS
    console.log('4. Configurando RLS rigoroso...');
    
    // Reports RLS
    await client.query('ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;');
    await client.query(`
      DO $$ BEGIN
        CREATE POLICY "Alunos criam reports" ON public.reports FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
      EXCEPTION
        WHEN duplicate_object THEN null;
      END $$;
    `);
    await client.query(`
      DO $$ BEGIN
        CREATE POLICY "Admins gerenciam reports" ON public.reports FOR ALL TO authenticated USING ((SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true);
      EXCEPTION
        WHEN duplicate_object THEN null;
      END $$;
    `);

    // Notifications RLS
    await client.query('ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;');
    await client.query(`
      DO $$ BEGIN
        CREATE POLICY "Todos leem notificacoes" ON public.notifications FOR SELECT TO authenticated USING (true);
      EXCEPTION
        WHEN duplicate_object THEN null;
      END $$;
    `);
    await client.query(`
      DO $$ BEGIN
        CREATE POLICY "Admins criam notificacoes" ON public.notifications FOR ALL TO authenticated USING ((SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true);
      EXCEPTION
        WHEN duplicate_object THEN null;
      END $$;
    `);

    // Ajuste Lessons para Ocultar Rascunhos
    console.log('5. Ajustando leitura de lições para ocultar rascunhos de alunos...');
    // Drop all previous SELECT policies on lessons safely (since we don't know the exact name)
    await client.query(`
      DO $$ DECLARE
          pol record;
      BEGIN
          FOR pol IN SELECT policyname FROM pg_policies WHERE tablename = 'lessons' AND cmd = 'SELECT'
          LOOP
              EXECUTE 'DROP POLICY IF EXISTS ' || quote_ident(pol.policyname) || ' ON public.lessons';
          END LOOP;
      END $$;
    `);
    await client.query(`
      CREATE POLICY "Leitura de licoes segregada" ON public.lessons FOR SELECT TO authenticated
      USING (
        is_draft = false OR (SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true
      );
    `);

    console.log('✅ Migração V2 concluída com sucesso!');
  } catch (err) {
    console.error('❌ Erro durante a migração V2:', err);
  } finally {
    client.release();
    await pool.end();
  }
}

migrate();
