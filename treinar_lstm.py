import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, random_split
import random

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
num_frames = 30           # Duração da sequência de cada vídeo (30 frames)
epochs = 120              # Retornado para 120 épocas da arquitetura anterior
batch_size = 8            # Tamanho do lote de processamento
learning_rate = 0.0005    # Taxa de aprendizado reduzida para estabilizar a descida do gradiente

# --- 🚀 FLAGS DE SELEÇÃO DE RECURSOS ---
COLETAR_ROSTO = False     # Mude para False para ignorar o rosto (258 features) e focar 100% nas mãos e pose.

# =====================================================================
# 📂 CARREGAMENTO DOS DADOS (.npy)
# =====================================================================
if not os.path.exists(DATA_PATH):
    print(f"[ERRO] A pasta '{DATA_PATH}' nao existe. Execute o coletar_dados.py primeiro.")
    exit(1)

# Lista todas as possíveis classes de sinais
todas_classes = [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d))]
todas_classes.sort()

X = []
y = []
classes_ativas = []

print("[INFO] Escaneando a pasta de dataset...")

for label in todas_classes:
    class_dir = os.path.join(DATA_PATH, label)
    files = os.listdir(class_dir)
    
    # Encontra IDs únicos de vídeos gravados nessa pasta
    video_ids = set()
    for file in files:
        if file.startswith("video_") and "_frame_" in file:
            try:
                parts = file.split("_")
                video_ids.add(int(parts[1]))
            except ValueError:
                continue
        elif file.startswith("video_") and file.endswith(".npy"):
            try:
                video_ids.add(int(file.replace("video_", "").replace(".npy", "")))
            except ValueError:
                continue
                
    video_ids = sorted(list(video_ids))
    temp_X = []
    
    # Carrega a sequência de 30 frames para cada vídeo
    for video in video_ids:
        window = []
        video_completo = True
        
        # Formato de Sequência Unificada (1 arquivo por vídeo)
        seq_path = os.path.join(class_dir, f'video_{video}.npy')
        if os.path.exists(seq_path):
            res = np.load(seq_path)
            if len(res) == num_frames:
                # Descarta pontos do rosto se COLETAR_ROSTO for False
                if not COLETAR_ROSTO and res.shape[1] == 1662:
                    res = np.concatenate([res[:, :132], res[:, 1536:]], axis=1)
                window = res
            else:
                video_completo = False
        else:
            # Formato de Frames Separados (30 arquivos por vídeo)
            for frame_num in range(num_frames):
                frame_path = os.path.join(class_dir, f'video_{video}_frame_{frame_num}.npy')
                if os.path.exists(frame_path):
                    res = np.load(frame_path)
                    # Descarta pontos do rosto se COLETAR_ROSTO for False
                    if not COLETAR_ROSTO and len(res) == 1662:
                        res = np.concatenate([res[:132], res[1536:]])
                    window.append(res)
                else:
                    video_completo = False
                    break
        
        if video_completo:
            temp_X.append(window)
            
    if len(temp_X) > 0:
        print(f"[OK] Sinal '{label}': {len(temp_X)} videos completos carregados.")
        classes_ativas.append(label)
        X.extend(temp_X)
        y.extend([label] * len(temp_X))
    else:
        print(f"[AVISO] Sinal '{label}': Nenhum video completo encontrado (pulando do treino).")

# Valida se há dados para treinar
if len(X) == 0:
    print("\n[ERRO] Nenhum video completo (de 30 frames) foi encontrado no dataset.")
    print("Por favor, execute o coletar_dados.py e grave pelo menos um sinal completo.")
    exit(1)

classes_ativas.sort()
num_classes_ativas = len(classes_ativas)

print(f"\n[INFO] Sinais Ativos no Treinamento ({num_classes_ativas}): {classes_ativas}")

if num_classes_ativas < 2:
    print("\n[AVISO] AVISO DE CLASSIFICAÇÃO:")
    print("Você possui apenas 1 sinal ativo gravado. Para treinar uma IA capaz de distinguir")
    print("sinais diferentes, você precisa de pelo menos 2 sinais ativos (ex: 'bom_dia' e 'pedir_ajuda').")
    print("O script continuará rodando para testar a compilação do modelo, mas o aprendizado real requer mais classes.\n")

# Mapeia as classes ativas para índices numéricos
class_map = {label: idx for idx, label in enumerate(classes_ativas)}
y_encoded = np.array([class_map[label] for label in y], dtype=np.int64)

X = np.array(X, dtype=np.float32)
y_tensor = torch.tensor(y_encoded)
X_tensor = torch.tensor(X)

print(f"[INFO] Dimensoes dos Dados de Entrada:")
print(f"   -> Amostras (Vídeos): {X.shape[0]}")
print(f"   -> Duração (Frames): {X.shape[1]}")
print(f"   -> Características por Frame (Features): {X.shape[2]}")

num_features = X.shape[2]

# =====================================================================
# 🧠 DEFINIÇÃO DA REDE NEURAL LSTM (CLASSIFICADOR SEQUENCIAL)
# =====================================================================
class ClassificadorLSTMLibras(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(ClassificadorLSTMLibras, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = 2
        
        # Camada LSTM padrão (Unidirecional)
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers=self.num_layers, 
            batch_first=True, 
            dropout=0.3
        )
        
        # Camada de Classificação Linear (Dense + ReLU + Dropout + Output)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x):
        # Inicializa o estado oculto (h0) e celular (c0) da LSTM
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        # Passa pela LSTM
        out, _ = self.lstm(x, (h0, c0))
        
        # Pega apenas a saída do ÚLTIMO frame da sequência (out[:, -1, :])
        out = self.fc(out[:, -1, :])
        return out

# =====================================================================
# 🔀 DIVISÃO DE TREINO E VALIDAÇÃO (80% / 20%)
# =====================================================================
dataset = TensorDataset(X_tensor, y_tensor)

val_size = int(len(dataset) * 0.2)
train_size = len(dataset) - val_size

# Proteções para datasets de teste muito pequenos
if val_size == 0 and len(dataset) > 1:
    val_size = 1
    train_size = len(dataset) - 1

if val_size > 0:
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    print(f"[INFO] Divisao de dados: {train_size} para Treino | {val_size} para Validacao")
else:
    train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    val_loader = None
    print(f"[AVISO] Dados insuficientes para divisao. Usando todas as {len(dataset)} amostras para treino.")

# =====================================================================
# 🚀 LOOP DE TREINAMENTO
# =====================================================================
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[INFO] Dispositivo de treino detectado: {device.type.upper()}")

# Inicializa o modelo
model = ClassificadorLSTMLibras(
    input_size=num_features, 
    hidden_size=128, 
    num_classes=num_classes_ativas
).to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

print("\n[INFO] Iniciando o treinamento...")

best_val_loss = float('inf')
best_model_state = None

for epoch in range(epochs):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for batch_x, batch_y in train_loader:
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)
        
        # Zero gradientes
        optimizer.zero_grad()
        
        # Forward pass
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        
        # Backward e otimização
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item() * batch_x.size(0)
        _, predicted = torch.max(outputs, 1)
        total += batch_y.size(0)
        correct += (predicted == batch_y).sum().item()
        
    epoch_loss = running_loss / total
    epoch_acc = (correct / total) * 100
    
    # Cálculo de métricas de validação
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
        
        # Salva o estado do modelo se a perda de validação diminuir
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = model.state_dict().copy()
    else:
        # Se não houver validação, monitora a perda de treino
        if epoch_loss < best_val_loss:
            best_val_loss = epoch_loss
            best_model_state = model.state_dict().copy()
        
    # Feedback no console a cada 5 épocas
    if (epoch + 1) % 5 == 0 or epoch == 0 or epoch == epochs - 1:
        val_info = f" | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%" if val_loader is not None else ""
        print(f"Época [{epoch+1}/{epochs}] -> Loss Treino: {epoch_loss:.4f} | Acc Treino: {epoch_acc:.2f}%{val_info}")

# =====================================================================
# 💾 SALVAR OS PESOS DO MELHOR MODELO DETECTADO
# =====================================================================
if best_model_state is not None:
    torch.save(best_model_state, 'modelo_lstm_libras.pth')
    print(f"\n[OK] Melhor checkpoint (Menor Val Loss: {best_val_loss:.4f}) salvo em 'modelo_lstm_libras.pth'!")
else:
    torch.save(model.state_dict(), 'modelo_lstm_libras.pth')
    print("\n[OK] Modelo treinado e salvo com sucesso em 'modelo_lstm_libras.pth'!")
print("[OK] Treinamento concluído!")
