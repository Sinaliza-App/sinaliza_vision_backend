from datetime import datetime, timezone
import os
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class FeedbackSample(Base):
    __tablename__ = "feedback_samples"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_file_path = Column(String, nullable=False)
    predicted_class = Column(String, nullable=False)
    corrected_class = Column(String, nullable=False)
    mode = Column(String, default="dinamico", nullable=True)  # "dinamico" ou "alfabeto"
    version = Column(String, default="v1", nullable=True)     # "v1", "v2", etc.
    device_info = Column(String, default="web", nullable=True)
    status = Column(String, default="pendente", nullable=False)  # "pendente", "validado", "rejeitado"
    reporter_role = Column(String, default="aluno", nullable=False)  # "aluno", "professor"
    reporter_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

# Configuração de conexão híbrida (Supabase PostgreSQL via .env ou SQLite local como fallback)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sinaliza_feedback.db"))
DATABASE_URL = os.getenv("FEEDBACK_DATABASE_URL") or os.getenv("DATABASE_URL")

if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Para Postgres do Supabase (ajusta prefixo postgresql se necessário)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Cria as tabelas do banco de dados caso não existam e aplica migrações não-destrutivas."""
    Base.metadata.create_all(bind=engine)
    
    # Migração segura para tabelas existentes
    try:
        with engine.begin() as conn:
            for col_name, col_type in [("mode", "VARCHAR"), ("version", "VARCHAR"), ("device_info", "VARCHAR")]:
                try:
                    conn.execute(text(f"ALTER TABLE feedback_samples ADD COLUMN {col_name} {col_type};"))
                except Exception:
                    pass
    except Exception:
        pass
                
    print(f"[OK] Banco de dados de Feedback/Coleta conectado via: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DB_PATH}")

def get_db():
    """Gerador de sessão de banco de dados para injeção de dependência."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
