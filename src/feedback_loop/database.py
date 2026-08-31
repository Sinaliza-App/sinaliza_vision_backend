from datetime import datetime, timezone
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class FeedbackSample(Base):
    __tablename__ = "feedback_samples"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_file_path = Column(String, nullable=False)
    predicted_class = Column(String, nullable=False)
    corrected_class = Column(String, nullable=False)
    status = Column(String, default="pendente", nullable=False)  # "pendente", "validado", "rejeitado"
    reporter_role = Column(String, default="aluno", nullable=False)  # "aluno", "professor"
    reporter_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

# Define o caminho absoluto para o banco SQLite na raiz do projeto
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sinaliza_feedback.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Cria as tabelas do banco de dados caso não existam."""
    Base.metadata.create_all(bind=engine)
    print(f"[OK] Banco de dados inicializado em: {DB_PATH}")

def get_db():
    """Gerador de sessão de banco de dados para injeção de dependência."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
