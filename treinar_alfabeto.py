import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, random_split
import random
from cv_utils import normalizar_vetor_keypoints

# Fixando sementes para estabilidade e reprodutibilidade do treino
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(42)

# =====================================================================
# 🔧 CONFIGURAÇÕES DO TREINAMENTO
# =====================================================================
DATA_PATH = 'dataset'
epochs = 80
batch_size = 16
learning_rate = 0.001

# --- 🚀 FLAGS DE SELEÇÃO DE RECURSOS ---
COLETAR_ROSTO = False     # False para focar apenas em pose e mãos (258 features)

# =====================================================================
# 📂 CARREGAMENTO DOS DADOS (.npy)
# =====================================================================
if not os.path.exists(DATA_PATH):
    print(f"[ERRO] A pasta '{DATA_PATH}' nao existe. Execute o coletar_dados.py primeiro.")
    exit(1)

# Lista todas as possíveis classes de letras (pastas com nomes maiúsculos ou de tamanho 1)
todas_classes = [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d))]
# Filtra apenas pastas que são de letras do alfabeto (comprimento 1 ou nomes específicos como C_CEDILHA)
letras_alfabeto = [c for c in todas_classes if len(c) == 1 or c == 'C_CEDILHA']
letras_alfabeto.sort()

X = []
y = []
classes_ativas = []

print("[INFO] Escaneando a pasta de dataset para o Alfabeto...")

for label in letras_alfabeto:
    class_dir = os.path.join(DATA_PATH, label)
    files = [f for f in os.listdir(class_dir) if f.endswith('.npy')]
    
    temp_frames = []
    
    for file in files:
        file_path = os.path.join(class_dir, file)
        try:
            res = np.load(file_path)
            
            # Trata se o arquivo for uma sequência 2D (seq_len, features)
            if len(res.shape) == 2:
                for frame in res:
                    # Corta o rosto se o modelo foi treinado sem
                    if not COLETAR_ROSTO and frame.shape[0] == 1662:
                        frame = np.concatenate([frame[:132], frame[1536:]])
                    
                    # Normaliza o frame (idempotente)
                    frame_norm = normalizar_vetor_keypoints(frame, tem_rosto=COLETAR_ROSTO)
                    temp_frames.append(frame_norm)
            
            # Trata se for um vetor 1D de frame único (features,)
            elif len(res.shape) == 1:
                if not COLETAR_ROSTO and res.shape[0] == 1662:
                    res = np.concatenate([res[:132], res[1536:]])
                
                # Normaliza o frame
                frame_norm = normalizar_vetor_keypoints(res, tem_rosto=COLETAR_ROSTO)
                temp_frames.append(frame_norm)
                
        except Exception as e:
            print(f"[AVISO] Erro ao carregar {file}: {e}")
            continue
            
    if len(temp_frames) > 0:
        print(f"[OK] Letra '{label}': {len(temp_frames)} amostras de frames carregadas.")
        classes_ativas.append(label)
        X.extend(temp_frames)
        y.extend([label] * len(temp_frames))
    else:
        print(f"[AVISO] Letra '{label}': Nenhuma amostra encontrada (pulando).")

if len(X) == 0:
    print("\n[ERRO] Nenhuma amostra de letra foi encontrada no dataset.")
    print("Por favor, ative o MODO_ALFABETO em coletar_dados.py e grave algumas letras primeiro.")
    exit(1)

classes_ativas.sort()
num_classes = len(classes_ativas)
print(f"\n[INFO] Letras Ativas no Treinamento ({num_classes}): {classes_ativas}")

# Mapeia as classes de letras para índices numéricos
class_map = {label: idx for idx, label in enumerate(classes_ativas)}
y_encoded = np.array([class_map[label] for label in y], dtype=np.int64)

X = np.array(X, dtype=np.float32)
y_tensor = torch.tensor(y_encoded)
X_tensor = torch.tensor(X)

print(f"[INFO] Dimensoes dos Dados de Entrada:")
print(f"   -> Amostras totais: {X.shape[0]}")
print(f"   -> Características por amostra: {X.shape[1]}")

num_features = X.shape[1]

# =====================================================================
# 🧠 DEFINIÇÃO DA REDE NEURAL MLP (CLASSIFICADOR ESTÁTICO)
# =====================================================================
class ClassificadorMLPAlfabeto(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(ClassificadorMLPAlfabeto, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )
        
    def forward(self, x):
        return self.network(x)

# =====================================================================
# 🔀 DIVISÃO DE TREINO E VALIDAÇÃO (80% / 20%)
# =====================================================================
dataset = TensorDataset(X_tensor, y_tensor)
val_size = int(len(dataset) * 0.2)
train_size = len(dataset) - val_size

# Proteções para datasets muito pequenos
if val_size == 0 and len(dataset) > 1:
    val_size = 1
    train_size = len(dataset) - 1

if val_size > 0:
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    print(f"[INFO] Divisao: {train_size} para Treino | {val_size} para Validacao")
else:
    train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    val_loader = None
    print(f"[AVISO] Amostras insuficientes para divisao. Usando tudo para treino.")

# =====================================================================
# 🚀 LOOP DE TREINAMENTO
# =====================================================================
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[INFO] Dispositivo de treino: {device.type.upper()}")

model = ClassificadorMLPAlfabeto(
    input_size=num_features, 
    hidden_size=128, 
    num_classes=num_classes
).to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

print("\n[INFO] Iniciando o treinamento do Alfabeto...")

best_val_loss = float('inf')
best_model_state = None

for epoch in range(epochs):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for batch_x, batch_y in train_loader:
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)
        
        optimizer.zero_grad()
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item() * batch_x.size(0)
        _, predicted = torch.max(outputs, 1)
        total += batch_y.size(0)
        correct += (predicted == batch_y).sum().item()
        
    epoch_loss = running_loss / total
    epoch_acc = (correct / total) * 100
    
    val_loss = 0.0
    val_acc = 0.0
    if val_loader is not None:
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                
                val_loss += loss.item() * batch_x.size(0)
                _, predicted = torch.max(outputs, 1)
                val_total += batch_y.size(0)
                val_correct += (predicted == batch_y).sum().item()
                
        val_loss = val_loss / val_total
        val_acc = (val_correct / val_total) * 100
        
        # Salva se o loss de validação diminuir
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = model.state_dict().copy()
    else:
        if epoch_loss < best_val_loss:
            best_val_loss = epoch_loss
            best_model_state = model.state_dict().copy()
            
    if (epoch + 1) % 10 == 0 or epoch == 0 or epoch == epochs - 1:
        val_info = f" | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%" if val_loader is not None else ""
        print(f"Epoca [{epoch+1}/{epochs}] -> Loss Treino: {epoch_loss:.4f} | Acc Treino: {epoch_acc:.2f}%{val_info}")

# =====================================================================
# 💾 SALVAR OS PESOS
# =====================================================================
if best_model_state is not None:
    torch.save(best_model_state, 'modelo_mlp_alfabeto.pth')
    print(f"\n[OK] Melhor checkpoint salvo em 'modelo_mlp_alfabeto.pth'!")
else:
    torch.save(model.state_dict(), 'modelo_mlp_alfabeto.pth')
    print("\n[OK] Modelo treinado e salvo em 'modelo_mlp_alfabeto.pth'!")

# Salva arquivo de mapeamento de classes para carregar depois no validador
import json
with open('class_map_alfabeto.json', 'w') as f:
    json.dump(classes_ativas, f)
print("[OK] Mapeamento de classes salvo em 'class_map_alfabeto.json'.")
print("[OK] Treinamento concluído com sucesso!")
