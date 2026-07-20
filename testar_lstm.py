import cv2
import numpy as np
import os
import mediapipe as mp
import torch
import torch.nn as nn
from collections import deque

# =====================================================================
# 🔧 CONFIGURAÇÕES DO TESTE
# =====================================================================
DATA_PATH = 'dataset'
MODEL_PATH = 'modelo_lstm_libras.pth'
num_frames = 30           # Duração do buffer de vídeo (30 frames)
CAMERA_INDEX = 0          # Índice da câmera
RESOLUCAO = (640, 480)    # Resolução de exibição
CONFIDENCE_THRESHOLD = 0.55  # Confiança mínima para considerar que o sinal está correto (reduzida de 0.65 para acomodar 32 classes)

# --- 🚀 FLAGS DE OTIMIZAÇÃO (Devem ser idênticas às usadas no coletar_dados.py!) ---
COLETAR_ROSTO = False
num_features = 1662 if COLETAR_ROSTO else 258

# =====================================================================
# 🧠 MODELO E CLASSES
# =====================================================================
class ClassificadorLSTMLibras(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(ClassificadorLSTMLibras, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = 2
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers=self.num_layers, 
            batch_first=True, 
            dropout=0.3
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

# Carrega a lista de classes na mesma ordem do treinamento
classes = [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d))]
classes.sort()
num_classes = len(classes)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print(f"[INFO] Classes ativas detectadas: {classes}")
print(f"[INFO] Carregando pesos do modelo de '{MODEL_PATH}'...")

if not os.path.exists(MODEL_PATH):
    print(f"[ERRO] O arquivo de pesos '{MODEL_PATH}' não foi encontrado. Execute o treinar_lstm.py primeiro.")
    exit(1)

# Inicializa o modelo e carrega os pesos
model = ClassificadorLSTMLibras(num_features, 128, num_classes).to(device)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.eval()

print("[OK] Modelo carregado com sucesso!")

# =====================================================================
# 🧠 MEDIAPIPE E AUXILIARES
# =====================================================================
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

def extrair_keypoints(results, coletar_rosto=True):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    mao_esq = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    mao_dir = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    
    if coletar_rosto:
        face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
        return np.concatenate([pose, face, mao_esq, mao_dir])
    else:
        return np.concatenate([pose, mao_esq, mao_dir])

# =====================================================================
# =====================================================================
# 🎥 FLUXO DE RECONHECIMENTO EM TEMPO REAL
# =====================================================================
print("🎥 Inicializando webcam...")
cap = cv2.VideoCapture(CAMERA_INDEX)
if not cap.isOpened():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

if not cap.isOpened():
    for i in [1, 2, 0]:
        if i == CAMERA_INDEX:
            continue
        cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"⚠️ Webcam no índice {CAMERA_INDEX} falhou. Usando índice {i} alternativo.")
            break

if not cap.isOpened():
    print(f"[ERRO] Não foi possível acessar a câmera no índice {CAMERA_INDEX} nem nos índices alternativos (1, 2).")
    print("Dicas de resolução de problemas:")
    print("1. Feche qualquer outro programa que possa estar usando a câmera (ex: Discord, Teams, Zoom, Navegador, etc).")
    print("2. Verifique se o seu app Flutter ou outro script python (como o coletar_dados.py) ainda está rodando em segundo plano e segurando a câmera.")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCAO[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCAO[1])

sequence = []
sinal_atual = "Detectando..."
confianca_atual = 0.0

# Deque para suavização das predições nos últimos 5 frames (evita oscilação brusca)
historico_predicoes = deque(maxlen=5)

try:
    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        print("\n[INFO] Webcam iniciada com sucesso!")
        print("[INFO] Fique posicionado e execute as expressões.")
        print("[INFO] Pressione [Q] na janela de vídeo para encerrar o teste.\n")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            # Espelhamento horizontal
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            # Processamento MediaPipe
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = holistic.process(image)
            image.flags.writeable = True
            frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            # Desenha os pontos chave da silhueta do usuário
            if COLETAR_ROSTO and results.face_landmarks:
                mp_drawing.draw_landmarks(frame, results.face_landmarks, mp_holistic.FACEMESH_CONTOURS,
                                         mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1))
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)
            if results.left_hand_landmarks:
                mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            if results.right_hand_landmarks:
                mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                
            # Extração de coordenadas e acúmulo no buffer temporal
            keypoints = extrair_keypoints(results, coletar_rosto=COLETAR_ROSTO)
            sequence.append(keypoints)
            sequence = sequence[-num_frames:] # Retém os últimos 30 frames coletados
            
            # Realiza a predição quando o buffer atinge 30 frames
            if len(sequence) == num_frames:
                # Converte para Tensor e roda inferência na Rede Neural
                input_data = torch.tensor([sequence], dtype=torch.float32).to(device)
                
                with torch.no_grad():
                    outputs = model(input_data)
                    probabilities = torch.softmax(outputs, dim=1)
                    confianca, predicao = torch.max(probabilities, 1)
                    
                sinal_predito = classes[predicao.item()]
                valor_confianca = confianca.item()
                
                # Se a confiança for alta, envia para votação, senão envia "Aguardando"
                if valor_confianca >= CONFIDENCE_THRESHOLD:
                    historico_predicoes.append(sinal_predito)
                else:
                    historico_predicoes.append("Aguardando...")
                
                # Votação do sinal majoritário para estabilizar o feedback visual
                sinal_mais_votado = max(set(historico_predicoes), key=historico_predicoes.count)
                
                if sinal_mais_votado != "Aguardando...":
                    sinal_atual = sinal_mais_votado
                    confianca_atual = valor_confianca
                else:
                    sinal_atual = "Aguardando..."
                    confianca_atual = 0.0

            # =====================================================================
            # 🎨 INTERFACE VISUAL (FEEDBACK EM TEMPO REAL)
            # =====================================================================
            # Barra horizontal no topo
            cor_barra = (39, 174, 96) if sinal_atual != "Aguardando..." else (142, 68, 173) # Verde se reconheceu, Roxo se aguardando
            cv2.rectangle(frame, (0, 0), (w, 55), cor_barra, -1)
            
            # Texto da barra
            if sinal_atual != "Aguardando...":
                texto_feedback = f"ACERTOU! GESTO: {sinal_atual.upper()} ({confianca_atual*100:.1f}%)"
            else:
                texto_feedback = "FACA UM GESTO DE LIBRAS..."
                
            cv2.putText(frame, texto_feedback, (15, 36), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Indicação de buffers e atalhos na base
            cv2.rectangle(frame, (0, h - 25), (w, h), (44, 62, 80), -1)
            cv2.putText(frame, f"Sincronia Câmera: {int((len(sequence)/num_frames)*100)}% | Pressione [Q] para Sair", (15, h - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (236, 240, 241), 1, cv2.LINE_AA)
            
            # Exibe a janela na tela
            cv2.imshow('Sinaliza App - Teste Real-Time (PIEC 2)', frame)
            
            # Verifica saída
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

except KeyboardInterrupt:
    print("\n🛑 Teste finalizado pelo teclado.")
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("🎥 Câmera fechada e recursos liberados.")
print("Teste encerrado.")
