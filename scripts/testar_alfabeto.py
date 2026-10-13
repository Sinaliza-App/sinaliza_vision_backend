import cv2
import numpy as np
import os
import mediapipe as mp
import torch
import torch.nn as nn
import json
from cv_utils import extrair_keypoints, normalizar_vetor_keypoints

# =====================================================================
# 🔧 CONFIGURAÇÕES DO TESTE
# =====================================================================
MODEL_PATH = 'modelo_mlp_alfabeto.pth'
CLASS_MAP_PATH = 'class_map_alfabeto.json'
CAMERA_INDEX = 0          # Índice da câmera
RESOLUCAO = (640, 480)    # Resolução de exibição
CONFIDENCE_THRESHOLD = 0.50  # Confiança mínima para aceitar a predição

# --- 🚀 FLAGS DE SELEÇÃO DE RECURSOS ---
COLETAR_ROSTO = False
num_features = 1662 if COLETAR_ROSTO else 258

# =====================================================================
# 🧠 MODELO E MAPA DE CLASSES
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

# Carrega o mapa de classes
if not os.path.exists(CLASS_MAP_PATH):
    print(f"[ERRO] O mapa de classes '{CLASS_MAP_PATH}' nao foi encontrado. Execute o treinar_alfabeto.py primeiro.")
    exit(1)

with open(CLASS_MAP_PATH, 'r') as f:
    classes = json.load(f)
num_classes = len(classes)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print(f"[INFO] Classes ativas detectadas: {classes}")
print(f"[INFO] Carregando pesos do modelo de '{MODEL_PATH}'...")

if not os.path.exists(MODEL_PATH):
    print(f"[ERRO] O arquivo de pesos '{MODEL_PATH}' nao foi encontrado. Execute o treinar_alfabeto.py primeiro.")
    exit(1)

# Inicializa o modelo e carrega pesos
model = ClassificadorMLPAlfabeto(num_features, 128, num_classes).to(device)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.eval()

print("[OK] Modelo carregado com sucesso!")

# =====================================================================
# 🧠 INICIALIZAÇÃO DO MEDIAPIPE
# =====================================================================
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

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
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCAO[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCAO[1])

letra_atual = "Aguardando..."
confianca_atual = 0.0

try:
    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        print("\n[INFO] Webcam iniciada com sucesso!")
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
            
            # Desenha os pontos chave na tela
            if COLETAR_ROSTO and results.face_landmarks:
                mp_drawing.draw_landmarks(frame, results.face_landmarks, mp_holistic.FACEMESH_CONTOURS,
                                         mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1))
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)
            if results.left_hand_landmarks:
                mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            if results.right_hand_landmarks:
                mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                
            # Extração, Normalização e Predição
            # Só faz inferência se pelo menos uma das mãos for detectada para evitar classificar ruído do corpo
            if results.left_hand_landmarks or results.right_hand_landmarks:
                keypoints = extrair_keypoints(results, coletar_rosto=COLETAR_ROSTO)
                keypoints_norm = normalizar_vetor_keypoints(keypoints, tem_rosto=COLETAR_ROSTO)
                
                # Converte para tensor e roda a inferência
                input_data = torch.tensor([keypoints_norm], dtype=torch.float32).to(device)
                
                with torch.no_grad():
                    outputs = model(input_data)
                    probabilities = torch.softmax(outputs, dim=1)
                    confianca, predicao = torch.max(probabilities, 1)
                    
                valor_confianca = confianca.item()
                sinal_predito = classes[predicao.item()]
                
                if valor_confianca >= CONFIDENCE_THRESHOLD:
                    letra_atual = sinal_predito
                    confianca_atual = valor_confianca
                else:
                    letra_atual = "Aguardando..."
                    confianca_atual = 0.0
            else:
                letra_atual = "Posicione a Mao"
                confianca_atual = 0.0

            # =====================================================================
            # 🎨 INTERFACE VISUAL (FEEDBACK EM TEMPO REAL)
            # =====================================================================
            # Barra horizontal no topo
            if letra_atual in ["Aguardando...", "Posicione a Mao"]:
                cor_barra = (142, 68, 173) # Roxo
                texto_feedback = "FAÇA UMA LETRA EM LIBRAS..." if letra_atual == "Aguardando..." else "POSICIONE SUA MÃO NA TELA"
            else:
                cor_barra = (46, 204, 113) # Verde
                texto_feedback = f"LETRA DETECTADA: {letra_atual.upper()} ({confianca_atual*100:.1f}%)"
                
            cv2.rectangle(frame, (0, 0), (w, 55), cor_barra, -1)
            cv2.putText(frame, texto_feedback, (15, 36), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Rodapé com instruções
            cv2.rectangle(frame, (0, h - 25), (w, h), (44, 62, 80), -1)
            cv2.putText(frame, "Visão Computacional Sinaliza App (Libras) | Pressione [Q] para Sair", (15, h - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (236, 240, 241), 1, cv2.LINE_AA)
            
            cv2.imshow('Sinaliza App - Validador do Alfabeto', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

except KeyboardInterrupt:
    print("\n🛑 Teste finalizado pelo teclado.")
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("🎥 Câmera liberada e janelas fechadas.")
print("Teste encerrado.")
