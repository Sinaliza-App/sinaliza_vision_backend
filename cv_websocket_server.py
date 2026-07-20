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
import torch
import torch.nn as nn
import mediapipe as mp

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
CONFIDENCE = 0.60  # Confiança mínima para YOLO
CONFIDENCE_LSTM = 0.55 # Confiança mínima para LSTM (31 classes)
PORTA_SERVIDOR = 8080

# ============================
# 🧠 ARQUITETURA LSTM
# ============================
class ClassificadorLSTMLibras(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(ClassificadorLSTMLibras, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = 2
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers=self.num_layers, 
            batch_first=True, 
            dropout=0.3
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

# Classes treinadas no LSTM (ordem alfabética, idêntica ao treinamento)
CLASSES_LSTM = ['amar', 'amarelo', 'aprender', 'azul', 'beber', 'bem_vindo', 'boa_noite', 'boa_tarde', 'bom_dia', 'branco', 'brincar_jogar', 'cachorro', 'cavalo', 'cinza', 'coelho', 'comer', 'comprar', 'estudar', 'gato', 'gostar', 'macaco', 'obrigado', 'oi', 'pedir_ajuda', 'preto', 'querer', 'trabalhar', 'tudo_bem', 'urso', 'verde', 'vermelho']

class DetectorLibras:
    """Classe responsável por carregar o modelo e fazer a inferência."""
    
    def __init__(self, model_path):
        # Define o diretório base (onde este script está)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Monta o caminho absoluto do modelo
        self.path_modelo = os.path.join(base_dir, model_path)
        
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

    def obter_gesto_suavizado(self, gesto_atual, confianca, is_movement=False):
        """
        Usa estatística para estabilizar a detecção.
        Só confirma o gesto se ele aparecer na maioria dos últimos frames.
        """
        if is_movement and gesto_atual:
            # Para movimentos rápidos, não exigimos repetição, pois a pose chave
            # pode durar apenas 1 ou 2 frames. Se detectou com confiança alta, aceita!
            return gesto_atual, confianca

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

class DetectorLibrasMovimento:
    """Classe responsável por detectar gestos dinâmicos usando MediaPipe e PyTorch LSTM."""
    
    def __init__(self, model_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.path_modelo = os.path.join(base_dir, model_path)
        self.carregado = False
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.num_features = 258 # Sem rosto, baseado no seu testar_lstm.py
        self.num_frames = 30
        self.buffer = deque(maxlen=self.num_frames)
        self.historico_predicoes = deque(maxlen=5)
        
        # Inicia MediaPipe Holistic
        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        self.carregar_modelo()
        
    def carregar_modelo(self):
        try:
            print(f"\n🧠 Carregando modelo LSTM de Movimento...")
            if not os.path.exists(self.path_modelo):
                print(f"❌ ERRO: Modelo '{self.path_modelo}' não encontrado!")
                return
                
            num_classes = len(CLASSES_LSTM)
            self.modelo = ClassificadorLSTMLibras(self.num_features, 128, num_classes).to(self.device)
            self.modelo.load_state_dict(torch.load(self.path_modelo, map_location=self.device))
            self.modelo.eval()
            self.carregado = True
            
            print(f"✅ Modelo LSTM carregado com sucesso (Device: {self.device})!")
            print(f"   -> {num_classes} Gestos Suportados.\n")
        except Exception as e:
            print(f"❌ Erro ao carregar LSTM: {e}")
            self.carregado = False

    def extrair_keypoints(self, results):
        pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
        mao_esq = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
        mao_dir = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
        return np.concatenate([pose, mao_esq, mao_dir])
            
    def processar_imagem(self, image):
        if not self.carregado: return None, 0.0
        
        # Converte a imagem BGR (OpenCV) para RGB (MediaPipe)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        results = self.holistic.process(image_rgb)
        
        keypoints = self.extrair_keypoints(results)
        self.buffer.append(keypoints)
        
        # Só prevê se tiver 30 frames no buffer
        if len(self.buffer) == self.num_frames:
            res_tensor = torch.tensor(np.array(self.buffer), dtype=torch.float32).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                pred = self.modelo(res_tensor)
                probs = torch.softmax(pred, dim=1)
                conf = torch.max(probs).item()
                idx = torch.argmax(probs).item()
                
            if conf > CONFIDENCE_LSTM:
                return CLASSES_LSTM[idx], conf
                
        return None, 0.0
        
    def obter_gesto_suavizado(self, gesto_atual, confianca, is_movement=True):
        if gesto_atual:
            self.historico_predicoes.append(gesto_atual)
        else:
            self.historico_predicoes.append(None)
            
        if len(self.historico_predicoes) < 3:
            return None, 0.0
            
        contador = Counter(self.historico_predicoes)
        if None in contador:
            del contador[None]
            
        if not contador:
            return None, 0.0
            
        gesto_comum, freq = contador.most_common(1)[0]
        # Suavização para movimento: maioria simples dos ultimos 5 frames
        if freq / len(self.historico_predicoes) >= 0.4:
            return gesto_comum, confianca
            
        return None, 0.0

# ===================================================================
# SERVIDOR WEBSOCKET (Lógica de Conexão)
# ===================================================================

detector_alfabeto: DetectorLibras = None
detector_movimento: DetectorLibras = None

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
                model_type = data.get('model_type', 'alfabeto')
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
            img_espelhada_h = cv2.flip(img_bgr, 1)

            # -----------------------------------------------------------
            # 3. Escolhe o detector correto
            # -----------------------------------------------------------
            if model_type == 'movimento' and detector_movimento is not None and detector_movimento.carregado:
                detector_ativo = detector_movimento
            else:
                detector_ativo = detector_alfabeto

            # 4. Detecta o gesto
            gesto_detectado, confianca = detector_ativo.processar_imagem(img_espelhada_h)
            
            # 5. Suaviza o resultado (tira a tremedeira)
            gesto_final, conf_final = detector_ativo.obter_gesto_suavizado(
                gesto_detectado, confianca, is_movement=(model_type == 'movimento')
            )

            # 5. Prepara a resposta
            if gesto_final:
                response = {
                    "prediction": gesto_final,
                    "confidence": float(conf_final)
                }
                # Log simples no terminal para você acompanhar
                print(f"🤟 Detectado: {gesto_final} ({conf_final:.2f})", end='\r')
            else:
                response = {
                    "prediction": "Nenhum",
                    "confidence": 0.0
                }
            
            # 6. Envia de volta para o Flutter
            await websocket.send(json.dumps(response))
            
    except websockets.exceptions.ConnectionClosed:
        print(f"\n🔌 Cliente desconectado: {websocket.remote_address}")
    except Exception as e:
        print(f"\n❌ Erro na conexão: {e}")

async def main():
    global detector_alfabeto, detector_movimento
    print("\n" + "="*60)
    print("🚀 SERVIDOR SINALIZA - VISÃO COMPUTACIONAL (MULTI-MODELO)")
    print("="*60)
    
    # Inicializa os detectores
    print("Carregando IA do Alfabeto...")
    detector_alfabeto = DetectorLibras("runs_novo/libras_fsl/weights/best.pt")
    
    print("Preparando IA de Movimento (LSTM)...")
    detector_movimento = DetectorLibrasMovimento("modelo_lstm_libras.pth")
    
    if not detector_alfabeto.carregado:
        print("Encerrando servidor por falta do modelo principal (Alfabeto).")
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