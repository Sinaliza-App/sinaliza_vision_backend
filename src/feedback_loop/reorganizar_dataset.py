import os
import shutil

def reorganizar():
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dataset_path = os.path.join(base_path, "dataset")
    
    if not os.path.exists(dataset_path):
        print(f"[ERRO] Pasta de dataset '{dataset_path}' não encontrada.")
        return
        
    # 1. Definir os novos caminhos
    treinamento_v1_path = os.path.join(dataset_path, "treinamento", "v1")
    feedback_paths = [
        os.path.join(dataset_path, "feedback", "bruto", "pendente"),
        os.path.join(dataset_path, "feedback", "bruto", "validado"),
        os.path.join(dataset_path, "feedback", "bruto", "rejeitado"),
        os.path.join(dataset_path, "feedback", "processado", "pendente"),
        os.path.join(dataset_path, "feedback", "processado", "validado"),
        os.path.join(dataset_path, "feedback", "processado", "rejeitado")
    ]
    
    # 2. Criar a estrutura de diretórios para feedback
    print("[INFO] Criando estrutura de pastas de feedback...")
    for path in feedback_paths:
        os.makedirs(path, exist_ok=True)
        print(f"   -> Criada/Verificada: {os.path.relpath(path, base_path)}")
        
    os.makedirs(treinamento_v1_path, exist_ok=True)
    print(f"   -> Criada/Verificada: {os.path.relpath(treinamento_v1_path, base_path)}")
    
    # 3. Mover classes de gestos atuais para treinamento/v1/
    excluir_pastas = {"treinamento", "feedback", ".git", ".github", "__pycache__"}
    
    print("[INFO] Movendo classes de gestos existentes para treinamento/v1/...")
    itens = os.listdir(dataset_path)
    
    moved_count = 0
    for item in itens:
        item_path = os.path.join(dataset_path, item)
        # Processar apenas diretórios que não estão na lista de exclusão
        if os.path.isdir(item_path) and item not in excluir_pastas:
            destino = os.path.join(treinamento_v1_path, item)
            print(f"   -> Movendo '{item}' para '{os.path.relpath(destino, base_path)}'...")
            try:
                shutil.move(item_path, destino)
                moved_count += 1
            except Exception as e:
                print(f"   [ERRO] Falha ao mover '{item}': {e}")
                
    print(f"[OK] Reorganização concluída. {moved_count} classes de gestos movidas para v1.")

if __name__ == "__main__":
    reorganizar()
