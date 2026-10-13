import os
import sys

# Adiciona a raiz do projeto ao path do Python para evitar erros de importação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.feedback_loop.database import SessionLocal, FeedbackSample

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VALIDATED_DIR = os.path.join(BASE_PATH, "dataset", "feedback", "bruto", "validado")
os.makedirs(VALIDATED_DIR, exist_ok=True)

def run_curator():
    print("\n" + "="*60)
    print("🛠️  SINALIZA APP - CURADOR DE FEEDBACK (CLI)")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Busca todas as amostras pendentes
        pendentes = db.query(FeedbackSample).filter(FeedbackSample.status == "pendente").all()
        
        if not pendentes:
            print("\n🎉 Nenhuma amostra pendente para curadoria. Bom trabalho!\n")
            return
            
        print(f"\n[INFO] Encontradas {len(pendentes)} amostras pendentes para revisão.\n")
        
        for idx, sample in enumerate(pendentes, 1):
            print(f"-"*40)
            print(f"Amostra {idx}/{len(pendentes)} (ID: {sample.id})")
            print(f"   -> Predição do Modelo: '{sample.predicted_class}'")
            print(f"   -> Correção do Usuário: '{sample.corrected_class}'")
            print(f"   -> Autor do Feedback: {sample.reporter_id} ({sample.reporter_role})")
            print(f"   -> Data/Hora: {sample.timestamp}")
            print(f"   -> Arquivo Físico: {sample.raw_file_path}")
            print(f"-"*40)
            
            while True:
                opcao = input("Escolha uma ação: [A]provar, [R]ejeitar, [P]ular, [S]air: ").strip().lower()
                
                if opcao == 's':
                    print("\n🛑 Encerrando curadoria. Até mais!\n")
                    return
                elif opcao == 'p':
                    print("⏭️ Amostra pulada.")
                    break
                elif opcao == 'a':
                    aprovar_amostra(db, sample)
                    break
                elif opcao == 'r':
                    rejeitar_amostra(db, sample)
                    break
                else:
                    print("❌ Opção inválida. Digite 'A', 'R', 'P' ou 'S'.")
                    
    finally:
        db.close()

def aprovar_amostra(db, sample):
    current_abs_path = os.path.join(BASE_PATH, sample.raw_file_path)
    new_file_name = os.path.basename(sample.raw_file_path)
    new_abs_path = os.path.join(VALIDATED_DIR, new_file_name)
    
    # Move o arquivo físico
    if os.path.exists(current_abs_path):
        try:
            os.rename(current_abs_path, new_abs_path)
            # Atualiza no banco
            sample.raw_file_path = os.path.relpath(new_abs_path, BASE_PATH)
            sample.status = "validado"
            db.commit()
            print(f"✅ Amostra {sample.id} APROVADA e movida para 'validado'.")
        except Exception as e:
            print(f"❌ Erro físico ao mover arquivo: {e}")
    else:
        print(f"⚠️ Erro: Arquivo físico '{current_abs_path}' não foi encontrado. Marcaremos como reprovada para limpeza.")
        sample.raw_file_path = ""
        sample.status = "rejeitado"
        db.commit()

def rejeitar_amostra(db, sample):
    current_abs_path = os.path.join(BASE_PATH, sample.raw_file_path)
    
    # Exclui o arquivo físico
    if os.path.exists(current_abs_path):
        try:
            os.remove(current_abs_path)
            print(f"🗑️ Arquivo físico deletado com sucesso para economizar espaço.")
        except Exception as e:
            print(f"❌ Erro ao deletar arquivo físico: {e}")
            
    # Atualiza banco de dados
    sample.raw_file_path = ""
    sample.status = "rejeitado"
    db.commit()
    print(f"❌ Amostra {sample.id} REJEITADA e removida da fila.")

if __name__ == "__main__":
    run_curator()
