# pyrefly: ignore [missing-import]
import cv2
import numpy as np
import os
import mediapipe as mp

# =====================================================================
# 🔧 CONFIGURAÇÕES DO USUÁRIO
# =====================================================================
DATA_PATH = os.path.join('dataset') 
sinais = np.array(['bom_dia', 'boa_tarde', 'comer', 'beber', 'pedir_ajuda', 'boa_noite', 'oi', 'tudo_bem', 'obrigado', 'bem_vindo', 'azul', 'amarelo', 'vermelho', 'preto', 'verde', 'cinza', 'branco', 'cachorro', 'gato', 'coelho', 'urso', 'macaco', 'cavalo', 'aprender', 'querer', 'amar', 'trabalhar', 'brincar_jogar', 'comprar', 'estudar', 'gostar'])
VIDEO_INICIAL = 0         # ID inicial do vídeo (mude se for coletar em grupo para evitar apagar arquivos dos outros)
num_videos = 30           # Quantidade de repetições por sinal
num_frames = 30           # Quantidade de frames por repetição
CAMERA_INDEX = 0          # Índice da câmera (normalmente 0)
RESOLUCAO = (640, 480)    # Resolução desejada da câmera (Largura, Altura)

# --- 🚀 FLAGS DE OTIMIZAÇÃO (Se alteradas, podem afetar a compatibilidade do seu dataset atual) ---
COLETAR_ROSTO = True       # Mantido True para compatibilidade. Mude para False se quiser acelerar o treino (desativa Face Mesh)
SALVAR_COMO_SEQUENCIA = False # Mantido False para compatibilidade (salva 1 arquivo por frame). Mude para True para salvar 1 arquivo por vídeo
# =====================================================================

# Criar as pastas automaticamente
for sinal in sinais:
    os.makedirs(os.path.join(DATA_PATH, sinal), exist_ok=True)

# =====================================================================
# 🧠 INICIALIZAÇÃO DO MEDIAPIPE
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
# 🎥 LOOP DE CAPTURA
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
    print(f"❌ ERRO: Não foi possível acessar a câmera no índice {CAMERA_INDEX} nem nos índices alternativos (1, 2).")
    print("Dicas de resolução de problemas:")
    print("1. Feche qualquer outro programa que possa estar usando a câmera (ex: Discord, Teams, Zoom, Navegador, etc).")
    print("2. Certifique-se de que outros scripts Python de teste ou o app Flutter não estão rodando em segundo plano.")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCAO[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCAO[1])

try:
    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        for sinal in sinais:
            video = VIDEO_INICIAL
            while video < VIDEO_INICIAL + num_videos:
                
                # [CHECK INTELIGENTE] Verifica se esta tentativa já foi concluída
                if SALVAR_COMO_SEQUENCIA:
                    check_path = os.path.join(DATA_PATH, sinal, f'video_{video}.npy')
                else:
                    check_path = os.path.join(DATA_PATH, sinal, f'video_{video}_frame_{num_frames-1}.npy')
                
                if os.path.exists(check_path):
                    video += 1
                    continue

                # --- ⏱️ PAUSA ENTRE TENTATIVAS ---
                for pausa_frame in range(30):
                    ret, frame = cap.read()
                    if not ret: break
                    frame = cv2.flip(frame, 1)
                    h, w, _ = frame.shape
                    
                    # Otimização de concorrência de leitura / flags
                    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image.flags.writeable = False
                    results = holistic.process(image)
                    image.flags.writeable = True
                    frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    
                    if results.left_hand_landmarks: 
                        mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                    if results.right_hand_landmarks: 
                        mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)

                    # Posicionamento de texto dinâmico
                    cv2.putText(frame, f'PREPARE-SE PARA: {sinal.upper()}', (int(w*0.1), int(h*0.4)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2, cv2.LINE_AA)
                    cv2.putText(frame, f'Tentativa #{video} iniciando...', (int(w*0.1), int(h*0.5)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1, cv2.LINE_AA)
                    
                    cv2.imshow('Coleta de Dados - Sinaliza App', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        raise KeyboardInterrupt

                # --- 🔴 GRAVAÇÃO REAL DO SINAL ---
                sequence_keypoints = []
                refazer_tentativa = False
                
                for frame_num in range(num_frames):
                    ret, frame = cap.read()
                    if not ret: break
                    frame = cv2.flip(frame, 1)
                    h, w, _ = frame.shape

                    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image.flags.writeable = False
                    results = holistic.process(image)
                    image.flags.writeable = True
                    frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                    # Desenhar landmarks
                    if COLETAR_ROSTO and results.face_landmarks: 
                        mp_drawing.draw_landmarks(frame, results.face_landmarks, mp_holistic.FACEMESH_CONTOURS, 
                                                 mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1))
                    if results.pose_landmarks: 
                        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)
                    if results.left_hand_landmarks: 
                        mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                    if results.right_hand_landmarks: 
                        mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)

                    # Textos e orientações
                    cv2.putText(frame, f'GRAVANDO: {sinal.upper()} | F:{frame_num}/{num_frames}', (15, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2, cv2.LINE_AA)
                    cv2.putText(frame, "[R] Refazer  |  [Q] Sair", (15, h - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
                    
                    cv2.imshow('Coleta de Dados - Sinaliza App', frame)

                    # Extrair keypoints
                    keypoints = extrair_keypoints(results, coletar_rosto=COLETAR_ROSTO)
                    if SALVAR_COMO_SEQUENCIA:
                        sequence_keypoints.append(keypoints)
                    else:
                        npy_path = os.path.join(DATA_PATH, sinal, f'video_{video}_frame_{frame_num}.npy')
                        np.save(npy_path, keypoints)

                    # Capturar teclas de atalho
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        raise KeyboardInterrupt
                    elif key == ord('r'):
                        print(f"🔄 Cancelando tentativa {video} a pedido do usuário. Reiniciando-a...")
                        refazer_tentativa = True
                        break

                if refazer_tentativa:
                    # Limpa qualquer arquivo parcial desta tentativa se salvou individualmente
                    if not SALVAR_COMO_SEQUENCIA:
                        for f in range(frame_num + 1):
                            temp_path = os.path.join(DATA_PATH, sinal, f'video_{video}_frame_{f}.npy')
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                    continue  # Reinicia o loop 'while' mantendo o mesmo índice 'video'

                # Se tudo correu bem e estamos salvando como sequência unificada
                if SALVAR_COMO_SEQUENCIA:
                    npy_path = os.path.join(DATA_PATH, sinal, f'video_{video}.npy')
                    np.save(npy_path, np.array(sequence_keypoints))

                video += 1  # Passa para o próximo vídeo/tentativa

except KeyboardInterrupt:
    print("\n🛑 Coleta interrompida pelo usuário.")
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("🎥 Câmera liberada e janelas fechadas com segurança.")

print("Coleta finalizada ou concluída com sucesso!")