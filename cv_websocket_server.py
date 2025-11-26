"""
Servidor WebSocket para o Sinaliza App
Atualizado para usar o novo modelo YOLO (runs_novo/libras_fsl/weights/best.pt)
"""

import asyncio
import websockets
import cv2
import os
import numpy as np
import json
import base64
from collections import deque, Counter

# Tenta importar o YOLO
try:
    from ultralytics import YOLO
except ImportError:
    print("❌ Erro: ultralytics não instalado!")
    print("Instale com: pip install ultralytics")
    exit(1)

# ============================
# 🔧 CONFIGURAÇÕES
# ============================
# Atualize este caminho se necessário, baseando-se na pasta onde o script roda
MODEL_PATH = "runs_novo/libras_fsl/weights/best.pt" 
CONFIDENCE = 0.60

class DetectorLibras:
    """Classe adaptadora para usar o YOLO no servidor."""
    
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Tenta encontrar o modelo no caminho absoluto ou relativo
        self.path_modelo = os.path.join(base_dir, MODEL_PATH)
        
        if not os.path.exists(self.path_modelo):
            # Fallback: tenta procurar na raiz se a pasta runs_novo estiver lá
            self.path_modelo = os.path.abspath(MODEL_PATH)

        self.modelo = None
        self.carregado = False
        
        # Histórico para suavizar o resultado (evitar que a letra fique piscando)
        self.historico_deteccoes = deque(maxlen=10)
        
        self.carregar_modelo()
    
    def carregar_modelo(self):
        try:
            print(f"📦 Carregando modelo YOLO: {self.path_modelo}")
            if not os.path.exists(self.path_modelo):
                print(f"❌ ARQUIVO DE MODELO NÃO ENCONTRADO EM: {self.path_modelo}")
                print("Verifique se a pasta 'runs_novo' está junto com este script.")
                self.carregado = False
                return

            self.modelo = YOLO(self.path_modelo)
            self.carregado = True
            print(f"✓ Modelo carregado! Classes: {list(self.modelo.names.values())}")
        except Exception as e:
            print(f"❌ Erro ao carregar modelo: {e}")
            self.carregado = False
    
    def processar_imagem(self, image):
        """Recebe imagem do OpenCV, faz predição e retorna o melhor resultado."""
        if not self.carregado:
            return None, 0.0

        # Inferência YOLO
        results = self.modelo.predict(image, conf=CONFIDENCE, verbose=False)
        
        melhor_resultado = None
        maior_confianca = 0.0

        # Processar resultados
        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                if conf > maior_confianca:
                    maior_confianca = conf
                    nome_classe = self.modelo.names[cls]
                    melhor_resultado = nome_classe

        return melhor_resultado, maior_confianca

    def obter_gesto_suavizado(self, gesto_atual, confianca):
        """Usa estatística para evitar 'flicks' (mudanças bruscas) na detecção."""
        if gesto_atual:
            self.historico_deteccoes.append(gesto_atual)
        
        if len(self.historico_deteccoes) < 3:
            return None, 0.0
            
        # Pega o gesto mais comum nos últimos frames
        contador = Counter(self.historico_deteccoes)
        gesto_comum, frequencia = contador.most_common(1)[0]
        
        # Se o gesto aparece na maioria dos frames recentes, confirma ele
        if frequencia / len(self.historico_deteccoes) >= 0.5:
            return gesto_comum, confianca
            
        return None, 0.0

# ===================================================================
# SERVIDOR WEBSOCKET
# ===================================================================

detector: DetectorLibras = None

async def handler(websocket):
    print(f"📱 Cliente Flutter conectado: {websocket.remote_address}")
    try:
        async for message in websocket:
            # 1. Receber JSON do Flutter
            data = json.loads(message)
            
            # 2. Decodificar imagem Base64
            img_bytes = base64.b64decode(data['image'])
            height = data['height']
            width = data['width']
            stride = data['stride']

            # 3. Reconstruir imagem para OpenCV
            img_gray = np.frombuffer(img_bytes, dtype=np.uint8).reshape((height, stride))
            img_gray = img_gray[:, :width] # Remover padding
            img_bgr = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
            
            # --- ROTAÇÃO (Mantenha se necessário para sua câmera) ---
            # img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE) 
            # -------------------------------------------------------

            # 4. Detecção
            gesto_detectado, confianca = detector.processar_imagem(img_bgr)
            
            # 5. Suavização (Para a UI do app ficar estável)
            gesto_final, conf_final = detector.obter_gesto_suavizado(gesto_detectado, confianca)

            # 6. Resposta
            if gesto_final:
                response = {
                    "gesto": gesto_final,
                    "confianca": float(conf_final)
                }
            else:
                response = {
                    "gesto": "Nenhum",
                    "confianca": 0.0
                }
            
            await websocket.send(json.dumps(response))
            
    except websockets.exceptions.ConnectionClosed:
        print(f"Cliente desconectado.")
    except Exception as e:
        print(f"Erro: {e}")

async def main():
    global detector
    print("\n" + "="*60)
    print("🚀 INICIANDO SERVIDOR SINALIZA (NOVO MODELO)")
    print("="*60)
    
    detector = DetectorLibras()
    
    if not detector.carregado:
        return

    async with websockets.serve(handler, "0.0.0.0", 8080):
        print(f"📡 Ouvindo na porta 8080...")
        print(f"🎯 Modelo: {MODEL_PATH}")
        print(f"🎚️  Confiança Mínima: {CONFIDENCE}")
        print("="*60 + "\n")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())