# pyrefly: ignore [missing-import]
import cv2
import numpy as np
import os
import mediapipe as mp
from cv_utils import extrair_keypoints, normalizar_vetor_keypoints

# =====================================================================
import argparse
parser = argparse.ArgumentParser(description="Coletor de Dados para o Sinaliza App")
parser.add_argument("--version", type=str, default="v1", help="Versão do dataset de treinamento de destino (padrão: v1)")
args = parser.parse_known_args()[0]

DATA_PATH = os.path.join('dataset', 'treinamento', args.version) 

# --- 🚀 MODO DE OPERAÇÃO: ALFABETO OU EXPRESSÕES ---
MODO_ALFABETO = True       # True para coletar Letras (A-Z e Ç), False para Expressões Dinâmicas (bom_dia, comer, etc.)

if MODO_ALFABETO:
    sinais = np.array(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'C_CEDILHA'])
    num_frames = 20        # Ajustado para 20 frames para capturar o movimento das letras dinâmicas de forma natural
else:
    sinais = np.array(['bom_dia', 'boa_tarde', 'comer', 'beber', 'pedir_ajuda', 'boa_noite', 'oi', 'tudo_bem', 'obrigado', 'bem_vindo', 'azul', 'amarelo', 'vermelho', 'preto', 'verde', 'cinza', 'branco', 'cachorro', 'gato', 'coelho', 'urso', 'macaco', 'cavalo', 'aprender', 'querer', 'amar', 'trabalhar', 'brincar_jogar', 'comprar', 'estudar', 'gostar'])
    num_frames = 30        # 30 frames por repetição para sinais dinâmicos

VIDEO_INICIAL = 0         # ID inicial do vídeo (mude se for coletar em grupo para evitar apagar arquivos dos outros)
num_videos = 30           # Quantidade de repetições por sinal
CAMERA_INDEX = 0          # Índice da câmera (normalmente 0)
RESOLUCAO = (640, 480)    # Resolução desejada da câmera (Largura, Altura)

# --- 🚀 FLAGS DE OTIMIZAÇÃO ---
COLETAR_ROSTO = False      # Mude para False para ignorar o rosto (258 features) e focar 100% nas mãos e pose.
SALVAR_COMO_SEQUENCIA = True # Mapeia como sequência para manter o diretório do dataset limpo e organizado
# =====================================================================

# Criar as pastas automaticamente
for sinal in sinais:
    os.makedirs(os.path.join(DATA_PATH, sinal), exist_ok=True)

# =====================================================================
# 🧠 INICIALIZAÇÃO DO MEDIAPIPE
# =====================================================================
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

# Função extrair_keypoints importada de cv_utils.py

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

def loop_pausado(cap, holistic):
    print("\n⏸️ Gravação pausada. Pressione [ESPAÇO] ou [P] para continuar...")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # Processa para mostrar o esqueleto na tela enquanto estiver pausado (feedback visual)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = holistic.process(image)
        image.flags.writeable = True
        frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        if results.left_hand_landmarks: 
            mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
        if results.right_hand_landmarks: 
            mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            
        # Desenha o overlay de Pausa
        cv2.putText(frame, "PAUSADO", (int(w*0.35), int(h*0.4)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "Pressione [ESPACO] ou [P] para continuar", (int(w*0.1), int(h*0.55)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "[Q] Sair", (int(w*0.42), int(h*0.65)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        
        cv2.imshow('Coleta de Dados - Sinaliza App', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' ') or key == ord('p'):
            print("▶️ Retomando gravação...")
            break
        elif key == ord('q'):
            raise KeyboardInterrupt

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
                    cv2.putText(frame, "[Espaco/P] Pausar  |  [Q] Sair", (15, h - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
                    
                    cv2.imshow('Coleta de Dados - Sinaliza App', frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        raise KeyboardInterrupt
                    elif key == ord(' ') or key == ord('p'):
                        loop_pausado(cap, holistic)

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
                    cv2.putText(frame, "[R] Refazer  |  [Espaco/P] Pausar  |  [Q] Sair", (15, h - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
                    
                    cv2.imshow('Coleta de Dados - Sinaliza App', frame)

                    # Extrair e normalizar keypoints
                    keypoints = extrair_keypoints(results, coletar_rosto=COLETAR_ROSTO)
                    keypoints_norm = normalizar_vetor_keypoints(keypoints, tem_rosto=COLETAR_ROSTO)
                    
                    if SALVAR_COMO_SEQUENCIA:
                        sequence_keypoints.append(keypoints_norm)
                    else:
                        npy_path = os.path.join(DATA_PATH, sinal, f'video_{video}_frame_{frame_num}.npy')
                        np.save(npy_path, keypoints_norm)

                    # Capturar teclas de atalho
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        raise KeyboardInterrupt
                    elif key == ord('r'):
                        print(f"🔄 Cancelando tentativa {video} a pedido do usuário. Reiniciando-a...")
                        refazer_tentativa = True
                        break
                    elif key == ord(' ') or key == ord('p'):
                        print(f"🔄 Gravação interrompida para pausa. A tentativa {video} será descartada e reiniciada ao retomar.")
                        refazer_tentativa = True
                        loop_pausado(cap, holistic)
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