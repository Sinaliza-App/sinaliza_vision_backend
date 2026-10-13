-- ==============================================================================
-- SINALIZA - MIGRAÇÃO V3: RBAC (ALUNO / PROFESSOR / ADMIN) & COLETA DE DADOS IA
-- ==============================================================================

-- 1. ADICIONAR COLUNA ROLE NA TABELA USERS
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'student';

-- Atualiza dados legados: quem tem is_admin = true vira 'admin', o restante 'student'
UPDATE public.users 
SET role = CASE 
    WHEN is_admin = TRUE THEN 'admin' 
    ELSE 'student' 
END 
WHERE role IS NULL OR role = '';

-- 2. TABELA DE CÓDIGOS DE CONVITE INSTITUCIONAIS
CREATE TABLE IF NOT EXISTS public.institution_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'teacher',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT now()
);

-- Insere código institucional padrão para professores
INSERT INTO public.institution_codes (code, role, description)
VALUES ('PROF-SINALIZA-2026', 'teacher', 'Código padrão institucional para cadastro de professores')
ON CONFLICT (code) DO UPDATE SET is_active = TRUE;

-- 3. TABELA DE AMOSTRAS DE COLETA & FEEDBACK DE IA (DATASET)
CREATE TABLE IF NOT EXISTS public.feedback_samples (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES public.users(id) ON DELETE SET NULL,
    auth_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    sign_name VARCHAR(100) NOT NULL,
    mode VARCHAR(20) DEFAULT 'dinamico', -- 'dinamico' (30 frames) ou 'alfabeto' (20 frames)
    raw_landmarks JSONB NOT NULL,        -- Matriz de keypoints 258 features
    status VARCHAR(20) DEFAULT 'pendente', -- 'pendente', 'validado', 'rejeitado'
    reporter_role VARCHAR(20) DEFAULT 'aluno', -- 'aluno' ou 'professor'
    corrected_sign VARCHAR(100),
    evaluator_id INT REFERENCES public.users(id) ON DELETE SET NULL,
    evaluator_notes TEXT,
    device_info VARCHAR(50) DEFAULT 'mobile',
    created_at TIMESTAMP DEFAULT now(),
    evaluated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_samples_status ON public.feedback_samples(status);
CREATE INDEX IF NOT EXISTS idx_feedback_samples_sign ON public.feedback_samples(sign_name);

-- 4. ATUALIZAR TRIGGER DE REGISTRO AUTOMÁTICO (auth.users -> public.users)
-- Permite que metadados passem a role e código institucional
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
DECLARE
    assigned_role VARCHAR(20) := 'student';
    invite_code TEXT;
BEGIN
    invite_code := new.raw_user_meta_data->>'institution_code';
    
    -- Se informou código institucional válido, concede papel de professor
    IF invite_code IS NOT NULL AND invite_code = 'PROF-SINALIZA-2026' THEN
        assigned_role := 'teacher';
    ELSIF new.raw_user_meta_data->>'role' = 'teacher' AND invite_code = 'PROF-SINALIZA-2026' THEN
        assigned_role := 'teacher';
    END IF;

    INSERT INTO public.users (auth_id, name, email, is_admin, role)
    VALUES (
        new.id, 
        COALESCE(new.raw_user_meta_data->>'name', 'Aluno'), 
        new.email,
        (assigned_role = 'admin'),
        assigned_role
    )
    ON CONFLICT (auth_id) DO UPDATE 
    SET 
        name = EXCLUDED.name,
        role = CASE WHEN public.users.role = 'admin' THEN 'admin' ELSE assigned_role END,
        is_admin = CASE WHEN public.users.is_admin = TRUE THEN TRUE ELSE (assigned_role = 'admin') END;

    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. ATUALIZAR RLS DE REPORTS E SAMPLES
ALTER TABLE public.feedback_samples ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Todos autenticados podem enviar amostras" ON public.feedback_samples;
CREATE POLICY "Todos autenticados podem enviar amostras" 
ON public.feedback_samples FOR INSERT 
TO authenticated 
WITH CHECK (true);

DROP POLICY IF EXISTS "Professores e admins visualizam amostras" ON public.feedback_samples;
CREATE POLICY "Professores e admins visualizam amostras" 
ON public.feedback_samples FOR SELECT 
TO authenticated 
USING (
    (SELECT role FROM public.users WHERE auth_id = auth.uid()) IN ('teacher', 'admin')
    OR (SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true
);

DROP POLICY IF EXISTS "Professores e admins avaliam amostras" ON public.feedback_samples;
CREATE POLICY "Professores e admins avaliam amostras" 
ON public.feedback_samples FOR UPDATE 
TO authenticated 
USING (
    (SELECT role FROM public.users WHERE auth_id = auth.uid()) IN ('teacher', 'admin')
    OR (SELECT is_admin FROM public.users WHERE auth_id = auth.uid()) = true
);
