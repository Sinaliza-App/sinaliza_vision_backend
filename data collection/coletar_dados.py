import cv2
import numpy as np
import os
import mediapipe as mp

# 1. Configurações Iniciais
DATA_PATH = os.path.join('dataset') 
sinais = np.array(['bom_dia', 'boa_tarde', 'comer', 'beber', 'ajuda'])
num_videos = 30      # Quantidade de vezes que você vai repetir cada sinal
num_frames = 30      # Quantidade de frames por repetição

# Criar as pastas automaticamente
for sinal in sinais:
    os.makedirs(os.path.join(DATA_PATH, sinal), exist_ok=True)

# 2. Inicializar o MediaPipe Holistic
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

def extrair_keypoints(results):
    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    mao_esq = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    mao_dir = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, face, mao_esq, mao_dir])

# 3. Loop de Captura
cap = cv2.VideoCapture(0)

with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
    
    for sinal in sinais:
        for video in range(num_videos):
            
            # [CHECK INTELEGENTE] Verifica se o último frame dessa tentativa já existe
            # Se já existir, pula o vídeo inteiro sem abrir a câmera para ele
            check_path = os.path.join(DATA_PATH, sinal, f'video_{video}_frame_{num_frames-1}.npy')
            if os.path.exists(check_path):
                continue

            # --- PAUSA ENTRE TENTATIVAS ---
            for pausa_frame in range(30):
                ret, frame = cap.read()
                if not ret: break
                frame = cv2.flip(frame, 1)
                
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = holistic.process(image)
                frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                if results.left_hand_landmarks: mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                if results.right_hand_landmarks: mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)

                cv2.putText(frame, f'PREPARE-SE PARA: {sinal.upper()}', (120,200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2, cv2.LINE_AA)
                cv2.putText(frame, f'Tentativa #{video} iniciando...', (120,240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1, cv2.LINE_AA)
                
                cv2.imshow('Coleta de Dados - Sinaliza App', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    exit()

            # --- GRAVAÇÃO REAL DO SINAL ---
            for frame_num in range(num_frames):
                ret, frame = cap.read()
                if not ret: break
                frame = cv2.flip(frame, 1)

                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = holistic.process(image)
                image.flags.writeable = True
                frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # Desenhar pontos na tela
                if results.face_landmarks: mp_drawing.draw_landmarks(frame, results.face_landmarks, mp_holistic.FACEMESH_CONTOURS, mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1))
                if results.pose_landmarks: mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)
                if results.left_hand_landmarks: mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                if results.right_hand_landmarks: mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)

                # Texto de gravação ativa
                cv2.putText(frame, f'GRAVANDO: {sinal.upper()} | F:{frame_num}/30', (15,30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2, cv2.LINE_AA)
                cv2.imshow('Coleta de Dados - Sinaliza App', frame)

                # Salvar Keypoints
                keypoints = extrair_keypoints(results)
                npy_path = os.path.join(DATA_PATH, sinal, f'video_{video}_frame_{frame_num}.npy')
                np.save(npy_path, keypoints)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    exit()
                    
    cap.release()
    cv2.destroyAllWindows()
print("Coleta finalizada ou já concluída com sucesso!")