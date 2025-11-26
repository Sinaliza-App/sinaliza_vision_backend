import cv2
import time
import os
from ultralytics import YOLO

# ============================
# 🔧 CONFIGURAÇÕES
# ============================

MODEL_PATH = "runs_novo/libras_fsl/weights/best.pt"
CONFIDENCE = 0.60
USE_WEBCAM = True
IMAGE_PATH = "test/images/1.jpg"

# ROI = região onde ficam as mãos
# valores em percentual do frame
ROI_TOP = 0.40   # 40% do topo é removido (onde fica o rosto)
ROI_BOTTOM = 1.00
ROI_LEFT = 0.05
ROI_RIGHT = 0.95


# ============================
# 🔥 APLICAR ROI
# ============================

def aplicar_roi(frame):
    h, w, _ = frame.shape

    top = int(h * ROI_TOP)
    bottom = int(h * ROI_BOTTOM)
    left = int(w * ROI_LEFT)
    right = int(w * ROI_RIGHT)

    recorte = frame[top:bottom, left:right]
    return recorte, (top, left)


# ============================
# 🔥 TESTANDO POR WEBCAM
# ============================

def testar_webcam(model):
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ ERRO: Webcam não encontrada.")
        return

    print("🎥 Webcam iniciada (Q para sair).")

    prev_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Falha ao capturar imagem.")
            break

        # Aplicar ROI (recorte das mãos)
        roi_frame, (offset_y, offset_x) = aplicar_roi(frame)

        # Rodar YOLO SOMENTE NA ROI
        results = model.predict(roi_frame, conf=CONFIDENCE, verbose=False)

        # Recriar frame anotado
        annotated = frame.copy()

        # Redesenhar caixas ajustando para o frame original
        for box in results[0].boxes:
            # Convertendo o tensor para valores Python normais
            x1, y1, x2, y2 = box.xyxy[0].tolist()  # <-- ESSENCIAL
            cls = int(box.cls[0])
            conf = float(box.conf[0])

            # Ajustar coordenadas para a posição original
            x1 = int(x1 + offset_x)
            y1 = int(y1 + offset_y)
            x2 = int(x2 + offset_x)
            y2 = int(y2 + offset_y)


            # Desenhar caixa
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Nome da classe
            label = f"{model.names[cls]} ({conf:.2f})"
            cv2.putText(annotated, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0), 2)

        # FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
        prev_time = curr_time

        cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 255, 0), 2)

        # Desenhar retângulo da ROI na imagem original
        h, w, _ = frame.shape
        cv2.rectangle(
            annotated,
            (int(w * ROI_LEFT), int(h * ROI_TOP)),
            (int(w * ROI_RIGHT), int(h * ROI_BOTTOM)),
            (255, 255, 0), 2
        )

        cv2.imshow("SinalizaApp - Detector com ROI", annotated)

        if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
            break

    cap.release()
    cv2.destroyAllWindows()


# ============================
# 🖼️ TESTE POR IMAGEM
# ============================

def testar_imagem(model, image_path):
    if not os.path.exists(image_path):
        print(f"❌ Erro: imagem '{image_path}' não encontrada.")
        return

    frame = cv2.imread(image_path)

    roi_frame, (offset_y, offset_x) = aplicar_roi(frame)
    results = model.predict(roi_frame, conf=CONFIDENCE)

    annotated = frame.copy()

    for box in results[0].boxes:
        x1, y1, x2, y2 = box.xyxy[0]
        cls = int(box.cls[0])
        conf = float(box.conf[0])

        x1 += offset_x
        x2 += offset_x
        y1 += offset_y
        y2 += offset_y
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

        cv2.rectangle(annotated, (x1, y1), (x2, y2),
                      (0, 255, 0), 2)

        label = f"{model.names[cls]} ({conf:.2f})"
        cv2.putText(annotated, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 0), 2)

    cv2.imshow("Resultado", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# ============================
# 🚀 MAIN
# ============================

if __name__ == "__main__":
    print("🔍 Carregando modelo...")
    model = YOLO(MODEL_PATH)

    print("🧠 Modelo carregado com sucesso!")

    if USE_WEBCAM:
        testar_webcam(model)
    else:
        testar_imagem(model, IMAGE_PATH)
