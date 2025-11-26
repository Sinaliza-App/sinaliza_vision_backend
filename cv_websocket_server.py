"""
Servidor WebSocket (com Debug Visual e Correção de Rotação 90 HORÁRIO)
"""

import asyncio
import websockets
import cv2
import os
import time
import numpy as np
import json
import base64
from collections import deque, Counter

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ Erro: ultralytics não instalado!")
    print("Instale com: pip install ultralytics")
    exit(1)

# --- Classe DetectorLibrasYOLO (sem mudanças) ---
class DetectorLibrasYOLO:
    def __init__(self, modelo_path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if modelo_path is None:
            possibilidades = [
                os.path.join(base_dir, 'modelo_yolo_libras.pt'),
                os.path.join(base_dir, 'runs', 'libras', 'train', 'weights', 'best.pt'),
                os.path.join(base_dir, 'best.pt')
            ]
            for path in possibilidades:
                if os.path.exists(path):
                    modelo_path = path
                    break
        if modelo_path is None or not os.path.exists(modelo_path):
            print(f"❌ Modelo YOLO não encontrado! Caminho procurado: {base_dir}")
            self.carregado = False
            return
        self.modelo_path = modelo_path
        self.modelo = None
        self.carregado = False
        self.historico_deteccoes = deque(maxlen=10)
        self.confianca_minima = 0.3
        self.carregar_modelo()
    
    def carregar_modelo(self):
        try:
            print(f"📦 Carregando modelo YOLO: {self.modelo_path}")
            self.modelo = YOLO(self.modelo_path)
            self.carregado = True
            print("✓ Modelo YOLO carregado com sucesso!")
            if hasattr(self.modelo, 'names'):
                print(f"✓ Classes: {list(self.modelo.names.values())}")
        except Exception as e:
            print(f"❌ Erro ao carregar modelo: {e}")
            self.carregado = False
    
    def detectar(self, image):
        if not self.carregado: return []
        results = self.modelo(image, verbose=False)
        deteccoes = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                bbox = box.xyxy[0].cpu().numpy()
                if conf >= self.confianca_minima:
                    classe_nome = self.modelo.names[cls]
                    deteccoes.append((classe_nome, conf, bbox))
        return deteccoes
    
    def gesto_suavizado(self, deteccoes):
        if not deteccoes: return None
        melhor = max(deteccoes, key=lambda x: x[1])
        self.historico_deteccoes.append(melhor[0])
        if len(self.historico_deteccoes) >= 5:
            contador = Counter(self.historico_deteccoes)
            classe_comum, freq = contador.most_common(1)[0]
            if freq / len(self.historico_deteccoes) >= 0.4:
                return melhor
        return None

# --- Servidor WebSocket (Com Correção) ---

detector: DetectorLibrasYOLO = None

async def handler(websocket):
    print(f"Um cliente (Flutter) se conectou: {websocket.remote_address}")
    try:
        async for message in websocket:
            data = json.loads(message)
            img_bytes = base64.b64decode(data['image'])
            height = data['height']
            width = data['width']
            stride = data['stride'] 

            img_gray = np.frombuffer(img_bytes, dtype=np.uint8).reshape((height, stride))
            img_gray = img_gray[:, :width]
            img_bgr = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
            
            # --- CORREÇÃO AQUI ---
            # Vamos tentar a última rotação: 90 graus no sentido HORÁRIO.
            img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
            # ---------------------

            img_debug = img_bgr.copy()
            
            deteccoes = detector.detectar(img_bgr)
            melhor_deteccao = detector.gesto_suavizado(deteccoes)

            # Desenha as detecções para debug
            for classe, conf, bbox in deteccoes:
                x1, y1, x2, y2 = map(int, bbox)
                cor = (0, 0, 255) # Vermelho
                if (melhor_deteccao and classe == melhor_deteccao[0]):
                    cor = (0, 255, 0) # Verde
                cv2.rectangle(img_debug, (x1, y1), (x2, y2), cor, 2)
                label = f"{classe} {conf*100:.1f}%"
                cv2.putText(img_debug, label, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)
            
            # Prepara a resposta JSON
            if melhor_deteccao:
                response_data = {"gesto": melhor_deteccao[0], "confianca": float(melhor_deteccao[1])}
            else:
                response_data = {"gesto": "Nenhum", "confianca": 0.0}
            
            # Re-ativa o envio da imagem de debug
            _, buffer = cv2.imencode('.jpg', img_debug)
            img_debug_base64 = base64.b64encode(buffer).decode('utf-8')
            response_data["debug_image"] = img_debug_base64
            
            await websocket.send(json.dumps(response_data))
            
    except websockets.exceptions.ConnectionClosed:
        print(f"Cliente desconectado: {websocket.remote_address}")
    except Exception as e:
        print(f"Ocorreu um erro com o cliente {websocket.remote_address}: {e}")

async def main():
    global detector
    detector = DetectorLibrasYOLO()
    if not detector.carregado:
        print("\n❌ Impossível iniciar o servidor WebSocket sem o modelo YOLO.")
        return
    async with websockets.serve(handler, "0.0.0.0", 8080):
        print("\n" + "="*70)
        print("🚀 SERVIDOR WEBSOCKET DE VISÃO COMPUTACIONAL INICIADO")
        print("Ouvindo na porta 8080 (ws://0.0.0.0:8080)")
        print("="*70 + "\n")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())