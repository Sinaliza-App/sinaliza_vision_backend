"""
Servidor WebSocket para o Sinaliza App (Versão Final)
Integra o modelo YOLO v8 com comunicação em tempo real para o Flutter.
"""

import asyncio
import websockets
import cv2
import os
import numpy as np
import json
import base64
from collections import deque, Counter
from datetime import datetime

# Tenta importar o YOLO
try:
    from ultralytics import YOLO
except ImportError:
    print("❌ Erro: ultralytics não instalado!")
    print("Instale com: pip install ultralytics")
    exit(1)

# ============================
# 🔧 CONFIGURAÇÕES GERAIS
# ============================
# Caminho exato que você me mostrou na imagem
MODEL_PATH = "runs_novo/libras_fsl/weights/best.pt" 
CONFIDENCE = 0.60  # Confiança mínima para considerar um acerto
PORTA_SERVIDOR = 8080

class DetectorLibras:
    """Classe responsável por carregar o modelo e fazer a inferência."""
    
    def __init__(self):
        # Define o diretório base (onde este script está)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Monta o caminho absoluto do modelo
        self.path_modelo = os.path.join(base_dir, MODEL_PATH)
        
        self.modelo = None
        self.carregado = False
        
        # Histórico para suavizar o resultado (evita que a letra fique "piscando")
        # Guarda as últimas 10 detecções para fazer uma média/votação
        self.historico_deteccoes = deque(maxlen=10)
        
        self.carregar_modelo()
    
    def carregar_modelo(self):
        try:
            print(f"\n📦 Carregando modelo YOLO...")
            print(f"   -> Caminho: {self.path_modelo}")
            
            if not os.path.exists(self.path_modelo):
                print(f"❌ ERRO CRÍTICO: Arquivo de modelo não encontrado!")
                print(f"   Verifique se a pasta 'runs_novo' está no mesmo local que este script.")
                self.carregado = False
                return

            self.modelo = YOLO(self.path_modelo)
            self.carregado = True
            
            # Pega os nomes das classes (letras) que o modelo conhece
            classes = list(self.modelo.names.values())
            print(f"✅ Modelo carregado com sucesso!")
            print(f"   -> Classes detectáveis: {classes}\n")
            
        except Exception as e:
            print(f"❌ Erro ao carregar modelo: {e}")
            self.carregado = False
    
    def processar_imagem(self, image):
        """Recebe uma imagem (array numpy), passa pelo YOLO e retorna o resultado."""
        if not self.carregado:
            return None, 0.0

        # Faz a predição usando o YOLO
        # verbose=False evita encher o terminal de logs
        results = self.modelo.predict(image, conf=CONFIDENCE, verbose=False)
        
        melhor_resultado = None
        maior_confianca = 0.0

        # O YOLO pode detectar vários objetos. Pegamos o com maior confiança.
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
        """
        Usa estatística para estabilizar a detecção.
        Só confirma o gesto se ele aparecer na maioria dos últimos frames.
        """
        if gesto_atual:
            self.historico_deteccoes.append(gesto_atual)
        else:
            # Se não detectou nada, adiciona 'None' ao histórico para diluir erros
            self.historico_deteccoes.append(None)
        
        # Precisa de um mínimo de dados para começar
        if len(self.historico_deteccoes) < 3:
            return None, 0.0
            
        # Conta qual gesto apareceu mais vezes nas últimas 10 tentativas
        contador = Counter(self.historico_deteccoes)
        # Remove os 'None' da contagem para focar nos gestos reais
        if None in contador:
            del contador[None]
            
        if not contador:
            return None, 0.0

        gesto_comum, frequencia = contador.most_common(1)[0]
        
        # Regra de Ouro: O gesto precisa aparecer em 50% dos quadros recentes
        # Isso evita "falsos positivos" rápidos que piscam na tela.
        if frequencia / len(self.historico_deteccoes) >= 0.5:
            return gesto_comum, confianca
            
        return None, 0.0

# ===================================================================
# SERVIDOR WEBSOCKET (Lógica de Conexão)
# ===================================================================

detector: DetectorLibras = None

async def handler(websocket):
    """Gerencia a conexão com o App Flutter."""
    print(f"📱 Cliente conectado: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            # 1. Recebe o JSON com a imagem Base64 do Flutter
            try:
                data = json.loads(message)
                img_base64 = data['image']
                height = data['height']
                width = data['width']
                stride = data['stride']
            except KeyError:
                print("⚠ Erro: JSON recebido com formato inválido.")
                continue
            
            # 2. Decodifica a imagem (Base64 -> Bytes -> Numpy Array)
            img_bytes = base64.b64decode(img_base64)
            
            # O Flutter envia YUV420. O canal Y (Luminância) é a imagem em escala de cinza.
            # É suficiente e mais rápido reconstruir apenas ele.
            img_gray = np.frombuffer(img_bytes, dtype=np.uint8).reshape((height, stride))
            
            # Remove o padding (bytes extras que o Android adiciona nas bordas)
            img_gray = img_gray[:, :width]

            # O YOLO precisa de 3 canais (RGB/BGR). Convertemos o cinza para BGR.
            img_bgr = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
            
            # -----------------------------------------------------------
            # 🔄 CORREÇÃO DE ROTAÇÃO (CRUCIAL)
            # A câmera do Flutter chega "deitada". Giramos 90º horário.
            # -----------------------------------------------------------
            # Tente esta rotação (Anti-horário)
            img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            img_espelhada_v = cv2.flip(img_bgr, 0)

            
            # 3. Detecta o gesto
            gesto_detectado, confianca = detector.processar_imagem(img_espelhada_v)
            
            # 4. Suaviza o resultado (tira a tremedeira)
            gesto_final, conf_final = detector.obter_gesto_suavizado(gesto_detectado, confianca)

            # 5. Prepara a resposta
            if gesto_final:
                response = {
                    "gesto": gesto_final,
                    "confianca": float(conf_final)
                }
                # Log simples no terminal para você acompanhar
                print(f"🤟 Detectado: {gesto_final} ({conf_final:.2f})", end='\r')
            else:
                response = {
                    "gesto": "Nenhum",
                    "confianca": 0.0
                }
            
            # 6. Envia de volta para o Flutter
            await websocket.send(json.dumps(response))
            
    except websockets.exceptions.ConnectionClosed:
        print(f"\n🔌 Cliente desconectado: {websocket.remote_address}")
    except Exception as e:
        print(f"\n❌ Erro na conexão: {e}")

async def main():
    global detector
    print("\n" + "="*60)
    print("🚀 SERVIDOR SINALIZA - VISÃO COMPUTACIONAL")
    print("="*60)
    
    # Inicializa o detector
    detector = DetectorLibras()
    
    if not detector.carregado:
        print("Encerrando servidor por falta de modelo.")
        return

    # Inicia o servidor
    # '0.0.0.0' permite conexões externas (Radmin VPN, Wi-Fi, etc.)
    print(f"📡 Aguardando conexões do Flutter na porta {PORTA_SERVIDOR}...")
    print("="*60 + "\n")
    
    async with websockets.serve(handler, "0.0.0.0", PORTA_SERVIDOR):
        await asyncio.Future()  # Mantém o script rodando para sempre

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Servidor encerrado pelo usuário.")