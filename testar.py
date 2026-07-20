import cv2
import time
import os
from ultralytics import YOLO

# ============================
# 🔧 CONFIGURAÇÕES DO USUÁRIO
# ============================

MODEL_PATH = "runs_novo/libras_fsl/weights/best.pt"
CONFIDENCE = 0.60  # confiança mínima
USE_WEBCAM = True  # True = webcam, False = imagem
IMAGE_PATH = "test/images/1.jpg"  # usado se USE_WEBCAM = False


# ============================
# 🔥 TESTE COM WEBCAM
# ============================

def testar_webcam(model):
    print("🎥 Inicializando webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
    if not cap.isOpened():
        for i in [1, 2]:
            cap = cv2.VideoCapture(i)
            if not cap.isOpened():
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                print(f"⚠️ Webcam no índice 0 falhou. Usando índice {i} alternativo.")
                break

    if not cap.isOpened():
        print("❌ ERRO: Não foi possível acessar a webcam em nenhum índice (0, 1, 2).")
        print("Certifique-se de que a câmera não está em uso por outro aplicativo (como Discord, Teams, Zoom, Flutter ou Navegador) e que os drivers estão atualizados.")
        return

    print("🎥 Webcam iniciada. Pressione 'Q' para sair.")

    prev_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Falha ao capturar frame da webcam.")
            break

        # Inferência YOLO
        results = model.predict(frame, conf=CONFIDENCE)

        # FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
        prev_time = curr_time

        # Desenhar resultados
        annotated_frame = results[0].plot()

        # Adicionar FPS no canto
        cv2.putText(annotated_frame, f"FPS: {fps:.1f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 2)

        cv2.imshow("SinalizaApp - Detector YOLO", annotated_frame)

        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break

    cap.release()
    cv2.destroyAllWindows()


# ============================
# 🖼️ TESTE COM IMAGEM ÚNICA
# ============================

def testar_imagem(model, image_path):
    if not os.path.exists(image_path):
        print(f"❌ A imagem '{image_path}' não existe.")
        return

    print(f"📸 Testando imagem: {image_path}")

    results = model.predict(image_path, conf=CONFIDENCE)

    # Mostrar janela com anotação
    annotated = results[0].plot()
    cv2.imshow("Resultado", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# ============================
# 📦 TESTE COM PASTA DE IMAGENS
# ============================

def testar_pasta(model, pasta):
    if not os.path.isdir(pasta):
        print(f"❌ A pasta '{pasta}' não existe.")
        return

    imagens = [f for f in os.listdir(pasta) if f.lower().endswith((".jpg", ".png"))]

    if not imagens:
        print("⚠ Nenhuma imagem encontrada na pasta.")
        return

    print(f"🗂 Testando {len(imagens)} imagens da pasta '{pasta}'...")

    for img in imagens:
        caminho = os.path.join(pasta, img)
        print(f"📸 {caminho}")

        results = model.predict(caminho, conf=CONFIDENCE)
        annotated = results[0].plot()

        cv2.imshow("Resultado", annotated)
        cv2.waitKey(500)

    cv2.destroyAllWindows()


# ============================
# 🚀 EXECUÇÃO PRINCIPAL
# ============================

if __name__ == "__main__":
    print("🔍 Carregando modelo...")
    model = YOLO(MODEL_PATH)

    print("🧠 Modelo carregado com sucesso!")

    if USE_WEBCAM:
        testar_webcam(model)
    else:
        # Troque entre imagem única ou pasta:
        testar_imagem(model, IMAGE_PATH)
        # testar_pasta(model, "test/images")
