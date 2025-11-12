import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import math
import time

# --- Inicialização do MediaPipe ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

# Histórico de posições (para detectar movimentos)
historico_posicoes = deque(maxlen=15)
ultimo_texto = ""
tempo_texto = 0

# Função para calcular a distância entre dois pontos
def distancia(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

# --- Funções de detecção de gestos ---
def detectar_oi(historico):
    """Detecta aceno lateral (mão aberta se movendo para os lados)."""
    if len(historico) < 5:
        return False
    deslocamento = np.mean([abs(historico[i+1][0] - historico[i][0]) for i in range(len(historico)-1)])
    return deslocamento > 15  # movimento lateral visível

def detectar_bom_dia(historico):
    """Detecta movimento vertical da mão (subindo e descendo)."""
    if len(historico) < 5:
        return False
    deslocamento = np.mean([abs(historico[i+1][1] - historico[i][1]) for i in range(len(historico)-1)])
    return deslocamento > 15  # movimento vertical visível

def detectar_tudo_bem(hand_landmarks, h, w):
    """Detecta gesto tipo 'ok' (indicador e polegar juntos)."""
    pontos = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark]
    dist = distancia(pontos[4], pontos[8])  # polegar e indicador
    return dist < 40  # se estiverem próximos

# --- Detecção de letras básicas ---
def detectar_letra(hand_landmarks, h, w):
    """Retorna 'A', 'B' ou 'C' conforme a posição dos dedos."""
    pontos = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark]

    # Dedo indicador = 8, médio = 12, anelar = 16, mínimo = 20, polegar = 4
    indicador = pontos[8][1] < pontos[6][1]  # se está estendido
    medio = pontos[12][1] < pontos[10][1]
    anelar = pontos[16][1] < pontos[14][1]
    minimo = pontos[20][1] < pontos[18][1]
    polegar = pontos[4][0] < pontos[3][0]

    # Heurísticas simples (apenas ilustrativas)
    if not indicador and not medio and not anelar and not minimo:
        return "A"  # punho fechado
    elif indicador and medio and anelar and minimo and not polegar:
        return "B"  # mão aberta
    elif indicador and medio and not anelar and not minimo:
        return "C"  # formato de "C"
    else:
        return None

# --- Captura de vídeo ---
cap = cv2.VideoCapture(0)

with mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
) as hands:

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("⚠️ Não foi possível capturar a imagem da câmera.")
            continue

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)
        image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        h, w, _ = image.shape

        texto_detectado = ""

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Desenha os pontos e conexões
                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style()
                )

                # Pega posição da palma (ponto 0)
                x_palma = int(hand_landmarks.landmark[0].x * w)
                y_palma = int(hand_landmarks.landmark[0].y * h)
                historico_posicoes.append((x_palma, y_palma))

                # --- Reconhecimentos ---
                if detectar_oi(historico_posicoes):
                    texto_detectado = "Oi"
                elif detectar_bom_dia(historico_posicoes):
                    texto_detectado = "Bom dia"
                elif detectar_tudo_bem(hand_landmarks, h, w):
                    texto_detectado = "Tudo bem?"
                else:
                    letra = detectar_letra(hand_landmarks, h, w)
                    if letra:
                        texto_detectado = letra

        # --- Exibir texto na tela ---
        if texto_detectado:
            ultimo_texto = texto_detectado
            tempo_texto = time.time()

        if time.time() - tempo_texto < 2:  # mostra por 2 segundos
            cv2.putText(image, ultimo_texto, (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4, cv2.LINE_AA)

        cv2.imshow("Sinaliza App - Detector de Gestos", image)

        if cv2.waitKey(5) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
