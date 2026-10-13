-- ==============================================================================
-- SINALIZA - MIGRAÇÃO V4: PERMISSÕES COMPLETAS PARA PROFESSORES (STAFF)
-- ==============================================================================

-- 1. FUNÇÃO AUXILIAR: is_staff() (Retorna TRUE para teacher ou admin)
CREATE OR REPLACE FUNCTION public.is_staff()
RETURNS boolean AS $$
DECLARE
    _is_admin BOOLEAN;
    _role VARCHAR(20);
BEGIN
    SELECT is_admin, role INTO _is_admin, _role FROM public.users WHERE auth_id = auth.uid() LIMIT 1;
    RETURN COALESCE(_is_admin, FALSE) OR (_role IN ('teacher', 'admin'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. FUNÇÃO AUXILIAR: is_admin() (Retorna TRUE apenas para administradores gerais)
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean AS $$
DECLARE
    _is_admin BOOLEAN;
    _role VARCHAR(20);
BEGIN
    SELECT is_admin, role INTO _is_admin, _role FROM public.users WHERE auth_id = auth.uid() LIMIT 1;
    RETURN COALESCE(_is_admin, FALSE) OR (_role = 'admin');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. PERMISSÕES NA TABELA USERS (Professores e Admins podem ler todos os usuários)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Usuários podem ver seu próprio perfil" ON public.users;
DROP POLICY IF EXISTS "Admins possuem acesso total aos users" ON public.users;
DROP POLICY IF EXISTS "Permissao de leitura em users" ON public.users;

CREATE POLICY "Permissao de leitura em users"
ON public.users FOR SELECT
TO authenticated
USING (
    auth_id = auth.uid() OR public.is_staff()
);

DROP POLICY IF EXISTS "Usuários podem atualizar seu próprio perfil" ON public.users;
DROP POLICY IF EXISTS "Permissao de update em users" ON public.users;

CREATE POLICY "Permissao de update em users"
ON public.users FOR UPDATE
TO authenticated
USING (
    auth_id = auth.uid() OR public.is_admin()
)
WITH CHECK (
    auth_id = auth.uid() OR public.is_admin()
);

-- 4. PERMISSÕES NA TABELA REPORTS (Professores e Admins podem ver e resolver)
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admins gerenciam reports" ON public.reports;
DROP POLICY IF EXISTS "Admins veem todos os reports" ON public.reports;
DROP POLICY IF EXISTS "Admins atualizam reports" ON public.reports;
DROP POLICY IF EXISTS "Admins possuem acesso total aos reports" ON public.reports;
DROP POLICY IF EXISTS "Staff veem todos os reports" ON public.reports;
DROP POLICY IF EXISTS "Staff atualizam reports" ON public.reports;

DROP POLICY IF EXISTS "Alunos criam reports" ON public.reports;
DROP POLICY IF EXISTS "Usuários inserem reports" ON public.reports;
CREATE POLICY "Alunos criam reports" 
ON public.reports FOR INSERT 
TO authenticated 
WITH CHECK (true);

CREATE POLICY "Staff veem todos os reports"
ON public.reports FOR SELECT
TO authenticated
USING (public.is_staff());

CREATE POLICY "Staff atualizam reports"
ON public.reports FOR UPDATE
TO authenticated
USING (public.is_staff())
WITH CHECK (public.is_staff());

-- 5. PERMISSÕES NA TABELA LESSONS E MODULES (Professores e Admins podem gerenciar)
ALTER TABLE public.lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.modules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Somente admins podem modificar lições" ON public.lessons;
DROP POLICY IF EXISTS "Staff podem gerenciar lições" ON public.lessons;
CREATE POLICY "Staff podem gerenciar lições"
ON public.lessons FOR ALL
TO authenticated
USING (public.is_staff())
WITH CHECK (public.is_staff());

DROP POLICY IF EXISTS "Somente admins podem modificar modulos" ON public.modules;
DROP POLICY IF EXISTS "Staff podem gerenciar modulos" ON public.modules;
CREATE POLICY "Staff podem gerenciar modulos"
ON public.modules FOR ALL
TO authenticated
USING (public.is_staff())
WITH CHECK (public.is_staff());

-- 6. PERMISSÕES NA TABELA FEEDBACK_SAMPLES
ALTER TABLE public.feedback_samples ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Professores e admins visualizam amostras" ON public.feedback_samples;
CREATE POLICY "Professores e admins visualizam amostras"
ON public.feedback_samples FOR SELECT
TO authenticated
USING (public.is_staff());

DROP POLICY IF EXISTS "Professores e admins avaliam amostras" ON public.feedback_samples;
CREATE POLICY "Professores e admins avaliam amostras"
ON public.feedback_samples FOR UPDATE
TO authenticated
USING (public.is_staff())
WITH CHECK (public.is_staff());
