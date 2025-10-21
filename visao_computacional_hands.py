import cv2
import mediapipe as mp

# Inicializa os módulos do MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands

# Configurações de desenho
pose_drawing_spec = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)
hands_drawing_spec = mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)

# Abre a câmera
cap = cv2.VideoCapture(0)

with mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as pose, mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as hands:

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("❌ Não foi possível acessar a câmera.")
            break

        # Converte para RGB (MediaPipe usa RGB)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # Processa o frame com pose e mãos
        pose_results = pose.process(image)
        hands_results = hands.process(image)

        # Volta para BGR para exibir
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # =====================
        # Desenha corpo (Pose)
        # =====================
        if pose_results.pose_landmarks:
            mp_drawing.draw_landmarks(
                image,
                pose_results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=pose_drawing_spec
            )

        # =====================
        # Desenha mãos
        # =====================
        if hands_results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(
                hands_results.multi_hand_landmarks, hands_results.multi_handedness
            ):
                label = handedness.classification[0].label  # 'Left' ou 'Right'
                cv2.putText(image, f'{label} Hand',
                            (10, 30 if label == 'Left' else 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    landmark_drawing_spec=hands_drawing_spec
                )

        # Mostra o resultado
        cv2.imshow('🖐️ Pose + Hands Detection', image)

        # Sai com 'q'
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

# Libera recursos
cap.release()
cv2.destroyAllWindows()
