import cv2
import mediapipe as mp

# Inicialização dos módulos do MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Inicializa a captura da câmera
cap = cv2.VideoCapture(0)

# Cria o objeto Hands do MediaPipe
with mp_hands.Hands(
    max_num_hands=2,          # Detecta até 2 mãos
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as hands:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Não foi possível capturar a imagem da câmera.")
            continue

        # Converte BGR (padrão OpenCV) para RGB (padrão MediaPipe)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Processa a imagem e detecta as mãos
        results = hands.process(image_rgb)

        # Converte de volta para BGR para exibir no OpenCV
        image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

        # Se detectar mãos:
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Desenha os pontos e conexões na mão
                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style()
                )

                # Exibe as coordenadas dos pontos
                h, w, _ = image.shape
                for id, lm in enumerate(hand_landmarks.landmark):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.putText(
                        image, str(id), (cx, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1
                    )
                    # (Opcional) printa as coordenadas no console
                    print(f"ID {id}: ({cx}, {cy})")

        # Exibe a imagem na tela
        cv2.imshow('Sinaliza - Rastreamento das mãos', image)

        # Sai com a tecla ESC
        if cv2.waitKey(5) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
