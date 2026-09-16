import os
import json
import uuid
import csv
import io
import numpy as np
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from src.feedback_loop.database import init_db, get_db, FeedbackSample
from src.feedback_loop.promover_dataset import promover

# Inicializa o banco de dados na inicialização do módulo
init_db()

app = FastAPI(title="Sinaliza Vision & Feedback API", version="2.0.0")

# Habilita CORS para permitir conexões do aplicativo Flutter e Dashboard Web
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

CLASS_MAP_ALFABETO_PATH = os.path.join(BASE_PATH, "class_map_alfabeto.json")
CLASS_MAP_LSTM_PATH = os.path.join(BASE_PATH, "class_map_lstm.json")
CLASSES_META_PATH = os.path.join(BASE_PATH, "classes_metadata.json")

# Garante que as pastas de destino existam
os.makedirs(PENDING_DIR, exist_ok=True)
os.makedirs(VALIDATED_DIR, exist_ok=True)

EXPECTED_FEATURES = 258

# =====================================================================
# MODELOS PYDANTIC
# =====================================================================

class ColetaSampleCreate(BaseModel):
    raw_keypoints: List[List[float]] = Field(
        ..., 
        description="Matriz de keypoints brutos de tamanho (num_frames, 258)"
    )
    class_name: str = Field(..., example="bom_dia")
    mode: str = Field("dinamico", description="'dinamico' (30 frames) ou 'alfabeto' (20 frames)")
    version: str = Field("v1", description="Versão do dataset (ex: 'v1', 'v2')")
    reporter_role: str = Field("professor", description="Papel do autor: 'professor' ou 'aluno'")
    reporter_id: Optional[str] = Field(None, example="prof_khalil")
    device_info: Optional[str] = Field("web_studio", description="Dispositivo/Canal de coleta")

class NovaClasseCreate(BaseModel):
    name: str = Field(..., example="computador")
    mode: str = Field("dinamico", description="'dinamico' ou 'alfabeto'")
    creator_role: str = Field("professor", description="Apenas professor pode criar novas classes")
    creator_id: Optional[str] = Field("admin", example="admin")

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

class PromoverDatasetRequest(BaseModel):
    source_version: str = Field("v1", example="v1")
    target_version: str = Field("v2", example="v2")

# =====================================================================
# ENDPOINTS DE CLASSES & METADADOS
# =====================================================================

@app.get("/api/classes")
def get_classes():
    """Retorna as classes oficiais ativas e novas classes em fase de coleta dinamicamente."""
    # 1. Carrega Alfabeto
    alfabeto_classes = []
    if os.path.exists(CLASS_MAP_ALFABETO_PATH):
        with open(CLASS_MAP_ALFABETO_PATH, "r", encoding="utf-8") as f:
            alfabeto_classes = json.load(f)
            
    # 2. Carrega LSTM (Expressões Dinâmicas)
    lstm_map = {}
    if os.path.exists(CLASS_MAP_LSTM_PATH):
        with open(CLASS_MAP_LSTM_PATH, "r", encoding="utf-8") as f:
            raw_lstm = json.load(f)
            if isinstance(raw_lstm, dict):
                lstm_map = {int(k): v for k, v in raw_lstm.items()}
            elif isinstance(raw_lstm, list):
                lstm_map = {i: v for i, v in enumerate(raw_lstm)}

    # 3. Carrega ou cria Metadados de Status das Classes
    meta = {}
    if os.path.exists(CLASSES_META_PATH):
        try:
            with open(CLASSES_META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    dinamico_classes = []
    for idx in sorted(lstm_map.keys()):
        c_name = lstm_map[idx]
        class_meta = meta.get(c_name, {
            "status": "em_producao",
            "min_amostras": 30,
            "descricao": f"Expressão: {c_name}"
        })
        
        # Conta amostras físicas existentes no v1 ou v2
        count_samples = 0
        v1_dir = os.path.join(DATASET_PATH, "treinamento", "v1", c_name)
        if os.path.exists(v1_dir):
            count_samples = len([f for f in os.listdir(v1_dir) if f.endswith(".npy")])
            
        dinamico_classes.append({
            "id": idx,
            "name": c_name,
            "status": class_meta.get("status", "em_producao"),
            "min_amostras": class_meta.get("min_amostras", 30),
            "samples_count": count_samples
        })

    return {
        "alfabeto": alfabeto_classes,
        "dinamico": dinamico_classes,
        "total_classes": len(alfabeto_classes) + len(dinamico_classes)
    }

@app.post("/api/classes", status_code=status.HTTP_201_CREATED)
def create_class(data: NovaClasseCreate):
    """Permite a um professor cadastrar um novo sinal no dataset."""
    if data.creator_role.lower() != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários com papel de 'professor' têm permissão para criar novas classes."
        )

    clean_name = data.name.strip().lower().replace(" ", "_")
    if not clean_name:
        raise HTTPException(status_code=400, detail="Nome da classe inválido.")

    # 1. Carrega ou atualiza Mapa de Classes LSTM
    lstm_map = {}
    if os.path.exists(CLASS_MAP_LSTM_PATH):
        with open(CLASS_MAP_LSTM_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
            lstm_map = {int(k): v for k, v in raw.items()} if isinstance(raw, dict) else {i: v for i, v in enumerate(raw)}

    # Verifica se já existe
    if clean_name in lstm_map.values():
        raise HTTPException(status_code=400, detail=f"A classe '{clean_name}' já existe no catálogo.")

    next_id = max(lstm_map.keys()) + 1 if lstm_map else 0
    lstm_map[next_id] = clean_name

    with open(CLASS_MAP_LSTM_PATH, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in sorted(lstm_map.items())}, f, indent=2, ensure_ascii=False)

    # 2. Registra Metadados como "aguardando_treinamento"
    meta = {}
    if os.path.exists(CLASSES_META_PATH):
        try:
            with open(CLASSES_META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    meta[clean_name] = {
        "status": "aguardando_treinamento",
        "created_by": data.creator_id,
        "created_at": datetime.now().isoformat(),
        "min_amostras": 30
    }
    with open(CLASSES_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # 3. Cria as pastas de destino
    os.makedirs(os.path.join(DATASET_PATH, "treinamento", "v1", clean_name), exist_ok=True)
    os.makedirs(os.path.join(DATASET_PATH, "treinamento", "v2", clean_name), exist_ok=True)

    return {
        "message": f"Classe '{clean_name}' criada com sucesso! Status: 'aguardando_treinamento'.",
        "id": next_id,
        "name": clean_name,
        "status": "aguardando_treinamento"
    }

# =====================================================================
# ENDPOINT DO ESTÚDIO DE COLETA (GRAVAÇÃO WEB / APP)
# =====================================================================

@app.post("/coleta/amostra", status_code=status.HTTP_201_CREATED)
def submit_coleta_sample(data: ColetaSampleCreate, db: Session = Depends(get_db)):
    """Recebe uma sequência de keypoints brutos (RAW) gravada no Estúdio Web ou Mobile."""
    arr = np.array(data.raw_keypoints, dtype=np.float32)
    
    # Validação de formato (deve ter 258 features por frame)
    if arr.ndim != 2 or arr.shape[1] != EXPECTED_FEATURES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de features inválido. Esperado (N, {EXPECTED_FEATURES}), obtido {arr.shape}"
        )
        
    expected_frames = 20 if data.mode == "alfabeto" else 30
    if arr.shape[0] != expected_frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantidade de frames inválida para modo '{data.mode}'. Esperado {expected_frames}, obtido {arr.shape[0]}"
        )
        
    if np.isnan(arr).any():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A amostra enviada contém valores NaN inválidos."
        )

    # 1. Determina destino físico por papel do usuário
    is_professor = data.reporter_role.lower() == "professor"
    target_status = "validado" if is_professor else "pendente"
    target_dir = VALIDATED_DIR if is_professor else PENDING_DIR
    
    # 2. Salva o arquivo fisicamente (.npy bruto sem normalizar)
    file_name = f"coleta_{data.class_name}_{uuid.uuid4().hex[:10]}.npy"
    file_path = os.path.join(target_dir, file_name)
    
    try:
        np.save(file_path, arr)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar arquivo .npy no disco: {e}"
        )

    # 3. Registra no banco de dados
    relative_path = os.path.relpath(file_path, BASE_PATH)
    sample = FeedbackSample(
        raw_file_path=relative_path,
        predicted_class=data.class_name,
        corrected_class=data.class_name,
        mode=data.mode,
        version=data.version,
        device_info=data.device_info or "web_studio",
        status=target_status,
        reporter_role=data.reporter_role,
        reporter_id=data.reporter_id or ("professor_web" if is_professor else "aluno_web")
    )
    
    db.add(sample)
    db.commit()
    db.refresh(sample)

    return {
        "message": "Amostra gravada e registrada com sucesso!",
        "sample_id": sample.id,
        "class_name": sample.corrected_class,
        "status": sample.status,
        "file_path": sample.raw_file_path,
        "xp_reward": 10 if data.reporter_role.lower() == "aluno" else 0
    }

# =====================================================================
# ENDPOINTS DE FEEDBACK, CURADORIA & PROMOÇÃO
# =====================================================================

@app.post("/feedback", status_code=status.HTTP_201_CREATED)
def create_feedback(data: FeedbackCreate, db: Session = Depends(get_db)):
    arr = np.array(data.raw_keypoints, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[1] != EXPECTED_FEATURES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de keypoints inválido. Esperado (N, {EXPECTED_FEATURES}), obtido {arr.shape}"
        )
        
    if np.isnan(arr).any():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A amostra enviada contém valores NaN inválidos."
        )

    is_professor = data.reporter_role.lower() == "professor"
    target_status = "validado" if is_professor else "pendente"
    target_dir = VALIDATED_DIR if is_professor else PENDING_DIR
    
    file_name = f"feedback_{uuid.uuid4().hex}.npy"
    file_path = os.path.join(target_dir, file_name)
    
    try:
        np.save(file_path, arr)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar arquivo de keypoints no disco: {e}"
        )
        
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
    samples = db.query(FeedbackSample).filter(FeedbackSample.status == "pendente").order_by(FeedbackSample.id.desc()).all()
    return [
        {
            "id": s.id,
            "predicted_class": s.predicted_class,
            "corrected_class": s.corrected_class,
            "mode": getattr(s, "mode", "dinamico"),
            "reporter_role": s.reporter_role,
            "reporter_id": s.reporter_id,
            "timestamp": s.timestamp.isoformat()
        } for s in samples
    ]

@app.post("/feedback/avaliar")
def evaluate_feedback(data: FeedbackEvaluate, db: Session = Depends(get_db)):
    sample = db.query(FeedbackSample).filter(FeedbackSample.id == data.feedback_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Amostra com ID {data.feedback_id} não encontrada."
        )
        
    if sample.status != "pendente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A amostra já está avaliada com o status: '{sample.status}'."
        )
        
    current_abs_path = os.path.join(BASE_PATH, sample.raw_file_path)
    
    if data.status.lower() == "validado":
        if data.corrected_class:
            sample.corrected_class = data.corrected_class
            
        new_file_name = os.path.basename(sample.raw_file_path)
        new_abs_path = os.path.join(VALIDATED_DIR, new_file_name)
        
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
            
        sample.raw_file_path = os.path.relpath(new_abs_path, BASE_PATH)
        sample.status = "validado"
        
    elif data.status.lower() == "rejeitado":
        if os.path.exists(current_abs_path):
            try:
                os.remove(current_abs_path)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao deletar fisicamente o arquivo: {e}"
                )
        sample.raw_file_path = ""
        sample.status = "rejeitado"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status inválido. Use 'validado' ou 'rejeitado'."
        )
        
    db.commit()
    db.refresh(sample)
    
    return {
        "message": f"Amostra avaliada como {sample.status.upper()}!",
        "feedback_id": sample.id,
        "status": sample.status,
        "corrected_class": sample.corrected_class
    }

@app.post("/feedback/promover")
def trigger_promotion(data: PromoverDatasetRequest):
    """Executa a consolidação das amostras validadas para a nova versão do dataset."""
    result = promover(source_version=data.source_version, target_version=data.target_version)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Erro desconhecido na promoção do dataset.")
        )
    return result

@app.get("/feedback/exportar-csv")
def export_csv(db: Session = Depends(get_db)):
    """Gera um arquivo CSV com o histórico de todas as amostras registradas no banco."""
    samples = db.query(FeedbackSample).order_by(FeedbackSample.id.asc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "predicted_class", "corrected_class", "mode", "version", "status", "reporter_role", "reporter_id", "raw_file_path", "timestamp"])
    
    for s in samples:
        writer.writerow([
            s.id,
            s.predicted_class,
            s.corrected_class,
            getattr(s, "mode", "dinamico"),
            getattr(s, "version", "v1"),
            s.status,
            s.reporter_role,
            s.reporter_id,
            s.raw_file_path,
            s.timestamp.isoformat() if s.timestamp else ""
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=manifesto_sinaliza.csv"}
    )
