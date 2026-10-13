-- Issue #8: Tabela de Feedback e MLOps

CREATE TABLE IF NOT EXISTS public.feedback_samples (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
  sign_name VARCHAR(100) NOT NULL,
  corrected_sign VARCHAR(100),
  source VARCHAR(50) DEFAULT 'mobile_app',
  reporter_role VARCHAR(20) DEFAULT 'student',
  status VARCHAR(20) DEFAULT 'pendente', -- pendente, aprovado, rejeitado, promovido
  version VARCHAR(20) DEFAULT 'v2',
  raw_file_path TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Índices para consultas rápidas do Dashboard de Curadoria
CREATE INDEX IF NOT EXISTS idx_feedback_status ON public.feedback_samples(status);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON public.feedback_samples(user_id);
