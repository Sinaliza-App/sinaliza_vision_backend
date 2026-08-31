import os
import uuid
import numpy as np
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from src.feedback_loop.database import init_db, get_db, FeedbackSample

# Inicializa o banco de dados na inicialização do módulo
init_db()

app = FastAPI(title="Sinaliza Vision Feedback API", version="1.0.0")

# Habilita CORS para permitir conexões do aplicativo Flutter e Web do Khalil
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_origins_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Caminhos base para salvar arquivos do dataset
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_PATH = os.path.join(BASE_PATH, "dataset")
PENDING_DIR = os.path.join(DATASET_PATH, "feedback", "bruto", "pendente")
VALIDATED_DIR = os.path.join(DATASET_PATH, "feedback", "bruto", "validado")

# Garante que as pastas de destino existam
os.makedirs(PENDING_DIR, exist_ok=True)
os.makedirs(VALIDATED_DIR, exist_ok=True)

# Mapeia as configurações de features esperadas
EXPECTED_FRAMES = 30
EXPECTED_FEATURES = 258

class FeedbackCreate(BaseModel):
    raw_keypoints: List[List[float]] = Field(
        ..., 
        description="Matriz de keypoints brutos de tamanho 30x258"
    )
    predicted_class: str = Field(..., example="bom_dia")
    corrected_class: str = Field(..., example="beber")
    reporter_id: Optional[str] = Field(None, example="professor_khalil")
    reporter_role: str = Field("aluno", description="Papel do relator: 'aluno' ou 'professor'")

class FeedbackEvaluate(BaseModel):
    feedback_id: int = Field(...)
    status: str = Field(..., description="Novo status: 'validado' ou 'rejeitado'")
    corrected_class: Optional[str] = Field(None, description="Permite corrigir a classe se necessário")

@app.post("/feedback", status_code=status.HTTP_201_CREATED)
def create_feedback(data: FeedbackCreate, db: Session = Depends(get_db)):
    # 1. Validação de formato da matriz
    arr = np.array(data.raw_keypoints, dtype=np.float32)
    if arr.shape != (EXPECTED_FRAMES, EXPECTED_FEATURES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de keypoints inválido. Esperado ({EXPECTED_FRAMES}, {EXPECTED_FEATURES}), obtido {arr.shape}"
        )
        
    if np.isnan(arr).any():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A amostra enviada contém valores NaN inválidos."
        )

    # 2. Determinar destino físico com base no papel do usuário
    is_professor = data.reporter_role.lower() == "professor"
    target_status = "validado" if is_professor else "pendente"
    target_dir = VALIDATED_DIR if is_professor else PENDING_DIR
    
    # 3. Salvar o arquivo fisicamente (.npy bruto)
    file_name = f"feedback_{uuid.uuid4().hex}.npy"
    file_path = os.path.join(target_dir, file_name)
    
    try:
        np.save(file_path, arr)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar arquivo de keypoints no disco: {e}"
        )
        
    # 4. Registrar no SQLite
    # Salva o caminho relativo no banco para portabilidade
    relative_path = os.path.relpath(file_path, BASE_PATH)
    
    sample = FeedbackSample(
        raw_file_path=relative_path,
        predicted_class=data.predicted_class,
        corrected_class=data.corrected_class,
        status=target_status,
        reporter_role=data.reporter_role,
        reporter_id=data.reporter_id
    )
    
    db.add(sample)
    db.commit()
    db.refresh(sample)
    
    return {
        "message": "Feedback registrado com sucesso!",
        "feedback_id": sample.id,
        "status": sample.status,
        "file_path": sample.raw_file_path
    }

@app.get("/feedback/pendentes")
def list_pending_feedbacks(db: Session = Depends(get_db)):
    samples = db.query(FeedbackSample).filter(FeedbackSample.status == "pendente").all()
    return [
        {
            "id": s.id,
            "predicted_class": s.predicted_class,
            "corrected_class": s.corrected_class,
            "reporter_role": s.reporter_role,
            "reporter_id": s.reporter_id,
            "timestamp": s.timestamp.isoformat()
        } for s in samples
    ]

@app.post("/feedback/avaliar")
def evaluate_feedback(data: FeedbackEvaluate, db: Session = Depends(get_db)):
    # 1. Localiza a amostra
    sample = db.query(FeedbackSample).filter(FeedbackSample.id == data.feedback_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Amostra de feedback com ID {data.feedback_id} não encontrada."
        )
        
    if sample.status != "pendente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A amostra já está avaliada com o status: '{sample.status}'."
        )
        
    # Caminho absoluto do arquivo atualmente no pendente
    current_abs_path = os.path.join(BASE_PATH, sample.raw_file_path)
    
    # 2. Tratar a decisão (Aprovar / Validar)
    if data.status.lower() == "validado":
        # Se houver correção na classe, atualiza no banco
        if data.corrected_class:
            sample.corrected_class = data.corrected_class
            
        # Determinar novo caminho físico no diretório de validados
        new_file_name = os.path.basename(sample.raw_file_path)
        new_abs_path = os.path.join(VALIDATED_DIR, new_file_name)
        
        # Mover o arquivo fisicamente
        if os.path.exists(current_abs_path):
            try:
                os.rename(current_abs_path, new_abs_path)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao mover arquivo de keypoints para validado: {e}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo físico da amostra não encontrado na pasta pendente."
            )
            
        # Atualiza o caminho no banco de dados e o status
        sample.raw_file_path = os.path.relpath(new_abs_path, BASE_PATH)
        sample.status = "validado"
        
    # 3. Tratar a decisão (Rejeitar)
    elif data.status.lower() == "rejeitado":
        # Excluir fisicamente o arquivo
        if os.path.exists(current_abs_path):
            try:
                os.remove(current_abs_path)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao deletar fisicamente o arquivo de keypoints rejeitado: {e}"
                )
                
        # Atualiza no banco de dados, limpando o caminho e mudando o status
        sample.raw_file_path = ""
        sample.status = "rejeitado"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status inválido para avaliação. Use 'validado' ou 'rejeitado'."
        )
        
    db.commit()
    db.refresh(sample)
    
    return {
        "message": f"Amostra avaliada como {sample.status.upper()}!",
        "feedback_id": sample.id,
        "status": sample.status,
        "corrected_class": sample.corrected_class
    }
