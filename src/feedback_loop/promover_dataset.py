import argparse
import os
import shutil
import sys
from datetime import datetime

# Adiciona a raiz do projeto ao path do Python para evitar erros de importação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.feedback_loop.database import SessionLocal, FeedbackSample

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_PATH = os.path.join(BASE_PATH, "dataset")
CHANGELOG_PATH = os.path.join(DATASET_PATH, "CHANGELOG.md")

def promover(source_version, target_version):
    source_dir = os.path.join(DATASET_PATH, "treinamento", source_version)
    target_dir = os.path.join(DATASET_PATH, "treinamento", target_version)
    
    # 1. Validações preliminares de diretórios
    if not os.path.exists(source_dir):
        print(f"[ERRO] Versão de origem '{source_version}' não encontrada em: {source_dir}")
        return
        
    if os.path.exists(target_dir):
        print(f"[ERRO] A versão de destino '{target_version}' já existe em: {target_dir}")
        print("Para manter a imutabilidade das versões, escolha um nome diferente (ex: v1.1).")
        return
        
    print(f"\n[INFO] Promovendo dataset '{source_version}' -> '{target_version}'...")
    
    # 2. Copia o dataset base
    print("   -> Copiando arquivos base...")
    try:
        shutil.copytree(source_dir, target_dir)
        print("   -> Cópia base concluída com sucesso.")
    except Exception as e:
        print(f"[ERRO] Falha ao copiar base do dataset: {e}")
        return
        
    # 3. Consulta as amostras validadas no banco de dados
    db = SessionLocal()
    samples_by_class = {}
    
    try:
        valid_samples = db.query(FeedbackSample).filter(FeedbackSample.status == "validado").all()
        
        if not valid_samples:
            print("[AVISO] Nenhuma amostra validada encontrada no banco para incorporar.")
        else:
            print(f"[INFO] Incorporando {len(valid_samples)} amostras validadas...")
            
            # Organiza as amostras por classe corrigida
            for sample in valid_samples:
                src_file_path = os.path.join(BASE_PATH, sample.raw_file_path)
                if not os.path.exists(src_file_path):
                    print(f"   [AVISO] Arquivo físico não encontrado: {sample.raw_file_path}. Pulando.")
                    continue
                    
                cls = sample.corrected_class
                samples_by_class.setdefault(cls, []).append(src_file_path)
                
            # Copia e renomeia as amostras no formato esperado pelo carregador de dados (video_{id}.npy)
            for cls, file_paths in samples_by_class.items():
                class_dir = os.path.join(target_dir, cls)
                os.makedirs(class_dir, exist_ok=True)
                
                # Encontra o maior índice de vídeo existente para esta classe
                existing_files = os.listdir(class_dir)
                max_id = -1
                for f in existing_files:
                    if f.startswith("video_") and f.endswith(".npy"):
                        try:
                            # Extrai o número do arquivo video_X.npy
                            num = int(f.replace("video_", "").replace(".npy", ""))
                            if num > max_id:
                                max_id = num
                        except ValueError:
                            continue
                            
                next_id = max_id + 1
                
                for src_path in file_paths:
                    dest_file_name = f"video_{next_id}.npy"
                    dest_path = os.path.join(class_dir, dest_file_name)
                    
                    shutil.copy(src_path, dest_path)
                    print(f"   -> [{cls}] Incorporada amostra como '{dest_file_name}'")
                    next_id += 1
                    
        # 4. Atualizar o CHANGELOG.md
        print("   -> Atualizando CHANGELOG.md...")
        escrever_changelog(target_version, source_version, samples_by_class)
        
        print(f"\n[OK] Versão '{target_version}' gerada com sucesso em: {target_dir}\n")
        
    finally:
        db.close()

def escrever_changelog(target_version, source_version, samples_by_class):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_added = sum(len(paths) for paths in samples_by_class.values())
    
    file_exists = os.path.exists(CHANGELOG_PATH)
    
    with open(CHANGELOG_PATH, "a", encoding="utf-8") as f:
        if not file_exists or os.path.getsize(CHANGELOG_PATH) == 0:
            f.write("# 📝 Dataset Changelog\n\n")
            
        f.write(f"## Versão {target_version} ({now_str})\n")
        f.write(f"- **Origem:** `{source_version}`\n")
        f.write(f"- **Amostras Adicionadas:** {total_added}\n")
        
        if total_added > 0:
            f.write("- **Distribuição por Classe:**\n")
            for cls, paths in samples_by_class.items():
                f.write(f"  - `{cls}`: +{len(paths)} amostras\n")
        f.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promove o dataset injetando os feedbacks validados.")
    parser.add_argument("--source", type=str, default="v1", help="Versão de origem (padrão: v1)")
    parser.add_argument("--target", type=str, required=True, help="Nova versão (ex: v1.1)")
    args = parser.parse_args()
    
    promover(args.source, args.target)
