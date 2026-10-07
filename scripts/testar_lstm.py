import cv2
import numpy as np
import os
import mediapipe as mp
import torch
from cv_utils import extrair_keypoints, normalizar_vetor_keypoints
from lstm_inference import LSTMInferenceManager

# =====================================================================
# 🔧 CONFIGURAÇÕES DO TESTE
# =====================================================================
DATA_PATH = 'dataset'
MODEL_PATH = 'modelo_lstm_libras.pth'
CLASS_MAP_PATH = 'class_map_lstm.json'
num_frames = 30           # Duração do buffer de vídeo (30 frames)
CAMERA_INDEX = 0          # Índice da câmera
RESOLUCAO = (640, 480)    # Resolução de exibição
CONFIDENCE_THRESHOLD = 0.55  # Confiança mínima para considerar que o sinal está correto (reduzida de 0.65 para acomodar 32 classes)

# --- 🚀 FLAGS DE OTIMIZAÇÃO (Devem ser idênticas às usadas no coletar_dados.py!) ---
COLETAR_ROSTO = False
num_features = 1662 if COLETAR_ROSTO else 258

# =====================================================================
# 🧠 MODELO E INFERÊNCIA
# =====================================================================
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Inicializa o gerenciador de inferência LSTM usando o arquivo persistente class_map_lstm.json
inference_manager = LSTMInferenceManager(
    model_path=MODEL_PATH,
    class_map_path=CLASS_MAP_PATH,
    num_frames=num_frames,
    input_size=num_features,
    confidence_threshold=CONFIDENCE_THRESHOLD,
    device=device
)

classes = inference_manager.classes
num_classes = len(classes)

print(f"[INFO] Classes ativas detectadas ({num_classes}): {classes}")
print("[OK] Modelo e mapeamento de classes carregados com sucesso!")

# =====================================================================
# 🧠 MEDIAPIPE E AUXILIARES
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
    print("Dicas de resolução de problemas:")
    print("1. Feche qualquer outro programa que possa estar usando a câmera (ex: Discord, Teams, Zoom, Navegador, etc).")
    print("2. Verifique se o seu app Flutter ou outro script python (como o coletar_dados.py) ainda está rodando em segundo plano e segurando a câmera.")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCAO[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCAO[1])

sinal_atual = "Detectando..."
confianca_atual = 0.0

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
            # Passo 1: Extrair raw completo (1662 features)
            keypoints_raw = extrair_keypoints(results, coletar_rosto=True)
            
            # Passo 2: Fatiar se COLETAR_ROSTO for False para obter (258 features)
            if not COLETAR_ROSTO:
                keypoints_sliced = np.concatenate([keypoints_raw[:132], keypoints_raw[1536:]])
            else:
                keypoints_sliced = keypoints_raw
            
            # Passo 3: Validar dimensionalidade intermediária
            assert keypoints_sliced.shape[0] == num_features, f"Erro: dimensão do frame fatiado é {keypoints_sliced.shape[0]}, esperado {num_features}"
            
            # Passo 4: Aplicar normalização
            keypoints_norm = normalizar_vetor_keypoints(keypoints_sliced, tem_rosto=COLETAR_ROSTO)
            
            # Passo 5: Validar resultado da normalização
            assert not np.isnan(keypoints_norm).any(), "Erro: NaN detectado após a normalização do frame em tempo real"
            assert keypoints_norm.shape[0] == num_features, f"Erro: dimensão do frame normalizado é {keypoints_norm.shape[0]}, esperado {num_features}"
            
            # Passo 6: Executar a predição através do manager de inferência
            sinal_atual, confianca_atual = inference_manager.predict_frame(keypoints_norm)

            # =====================================================================
            # 🎨 INTERFACE VISUAL (FEEDBACK EM TEMPO REAL)
            # =====================================================================
            # Barra horizontal no topo
            cor_barra = (39, 174, 96) if sinal_atual != "Aguardando..." and sinal_atual != "Detectando..." else (142, 68, 173) # Verde se reconheceu, Roxo se aguardando/detectando
            cv2.rectangle(frame, (0, 0), (w, 55), cor_barra, -1)
            
            # Texto da barra
            if sinal_atual != "Aguardando..." and sinal_atual != "Detectando...":
                texto_feedback = f"ACERTOU! GESTO: {sinal_atual.upper()} ({confianca_atual*100:.1f}%)"
            elif sinal_atual == "Detectando...":
                texto_feedback = "INICIALIZANDO FILA DE QUADROS..."
            else:
                texto_feedback = "FACA UM GESTO DE LIBRAS..."
                
            cv2.putText(frame, texto_feedback, (15, 36), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Indicação de buffers e atalhos na base
            cv2.rectangle(frame, (0, h - 25), (w, h), (44, 62, 80), -1)
            cv2.putText(frame, f"Sincronia Câmera: {int((len(inference_manager.sequence)/num_frames)*100)}% | Pressione [Q] para Sair", (15, h - 8),
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
